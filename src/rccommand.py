###
### Copyright 2002 Ximian, Inc.
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the GNU General Public License as published by
### the Free Software Foundation, version 2 of the License.
###
### This program is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
### GNU General Public License for more details.
###
### You should have received a copy of the GNU General Public License
### along with this program; if not, write to the Free Software
### Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
###

import sys
import os
import getopt
import string
import rcformat
import rctalk

default_opt_table = [
    ["U", "user",     "username", "Specify user name"],
    ["P", "password", "password", "Specify password"],
    ["h", "host",     "hostname", "Contact daemon on specified host"],
    ["",  "version",  "",         "Print client version and exit"],
    ["V", "verbose",  "",         "Verbose output"],
    ["",  "normal-output", "",    "Normal output (default)"],
    ["t", "terse",    "",         "Terse output"],
    ["",  "quiet",    "",         "Quiet output, print only error messages"],
    ["",  "read-from-file", "filename",   "Get args from file"],
    ["",  "read-from-stdin", "",  "Get args from stdin"],
    ["",  "ignore-rc-file", "",   "Don't read rc's startup file (~/.rcrc)"],
    ["",  "ignore-env", "",       "Ignore the RC_ARGS environment variable"],
    ["?", "help",     "",         "Get help on a specific command"]
]

default_orthogonal_opts = [["verbose", "terse", "normal-output", "quiet"]]


command_dict = {}
alias_dict = {}


def register(constructor):
    obj = constructor()
    name = obj.name()
    aliases = obj.aliases()
    hidden = obj.is_hidden()
    description = obj.description_short() or "<No Description Available>"
    category = obj.category()

    if command_dict.has_key(name):
        rctalk.error("Command name collision: '"+name+"'")
    else:
        command_dict[name] = (description, constructor, aliases, hidden, category)

    for a in aliases:
        al = string.lower(a)
        if command_dict.has_key(al):
            rctalk.error("Command/alias collision: '"+a+"'")
        elif alias_dict.has_key(al):
            rctalk.error("Alias collision: '"+a+"'")
        else:
            alias_dict[al] = name


def construct(name):
    nl = string.lower(name)

    if alias_dict.has_key(nl):
        nl = alias_dict[nl]

    if not command_dict.has_key(nl):
        rctalk.warning("Unknown command '"+name+"'")
        return None

    cons = command_dict[nl][1]

    return cons()

def print_command_list(commands):

    max_len = 0
    cmd_list = []
    
    for c in commands:
        name, aliases, description = c

        if aliases:
            name = name + " (" + string.join(aliases, ", ") + ")"
            
        cmd_list.append([name, description])
        max_len = max(max_len, len(name))

    desc_len = max_len + 4

    for c in cmd_list:

        # If, for some reason, the command list is *really* wide (which it never should
        # be), don't do something stupid.
        if 79 - desc_len > 10:
            desc = rcformat.linebreak(c[1], 79-desc_len)
        else:
            desc = [c[1]]
                
        desc_first = desc.pop(0)
        rctalk.message("  " + string.ljust(c[0], max_len) + "  " + desc_first)
        for d in desc:
            rctalk.message(" " * desc_len + d)

def usage_basic():
    rctalk.message("Usage: rc <command> <options> ...")
    rctalk.message("")

    keys = command_dict.keys()

    if keys:
        keys.sort()
        command_list = []
        for k in keys:
            description, constructor, aliases, hidden, category  = command_dict[k]
            if not hidden and string.lower(category) == "basic":
                command_list.append([k, aliases, description])

        rctalk.message("Some basic commands are:")
        print_command_list(command_list)

        rctalk.message("")
        rctalk.message("For a more complete list of commands and important options,")
        rctalk.message("run rc with the --help option.")

    else:
        rctalk.error("<< No commands found --- something is wrong! >>")

def usage_full():
    rctalk.message("Usage: rc <command> <options> ...")
    rctalk.message("")

    rctalk.message("The following options are understood by all commands:")
    rcformat.opt_table(default_opt_table)
    rctalk.message("")

    keys = command_dict.keys()

    if keys:
        keys.sort()
        command_list = []
        for k in keys:
            description, constructor, aliases, hidden, category  = command_dict[k]
            if not hidden:
                command_list.append([k, aliases, description])

        rctalk.message("Valid commands are:")
        print_command_list(command_list)

        rctalk.message("")
        rctalk.message("For more detailed information about a specific command,")
        rctalk.message("run 'rc <command name> --help'.")

    else:
        rctalk.error("<< No commands found --- something is wrong! >>")


def extract_command_from_argv(argv):
    command = None
    i = 0
    while i < len(argv) and not command:
        if argv[i][0] != "-":
            command = construct(argv[i])
            if command:
                argv.pop(i)
        else:
            takes_arg = 0
            for o in default_opt_table:
                if not (argv[i][1:] == o[0] or argv[i][2:] == o[1]):
                    continue

                if o[2] != "":
                    takes_arg = 1
                    break

            if takes_arg and string.find(argv[i], "=") == -1:
                i = i + 1

        i = i + 1

    if not command:
        rctalk.warning("No command found on command line.")
        if "--help" in argv or "-?" in argv:
            usage_full()
        else:
            usage_basic()
        sys.exit(1)

    return command

###
### Handle .rcrc, RC_ARGS, --read-from-file and --read-from-stdin
###

def expand_synthetic_args(argv, command_name):

    # We add arguments to the beginning of argv.  This means we can
    # override an magically added arg by explicitly putting the
    # orthogonal arg on the command line.
    def join_args(arglist, argv):
        return map(string.strip, arglist) + argv

    # Try to read the .rcrc file.  It basically works like a .cvsrc file.
    if "--ignore-rc-file" not in argv:
        try:
            rcrc = open(os.path.expanduser("~/.rcrc"), "r")
            while 1:
                line = rcrc.readline()

                # strip out comments
                hash_pos = string.find(line, "#")
                if hash_pos >= 0:
                    line = line[0:hash_pos]

                # skip empty lines
                if not line:
                    break
                
                pieces = string.split(line)
                if len(pieces) and pieces[0] == command_name:
                    argv = join_args(pieces[1:], argv)
            rcrc.close()
            
        except IOError:
            # If we can't open the .rcrc file, that is fine... just
            # continue as if nothing happened.
            pass

    if "--ignore-env" not in argv and os.environ.has_key("RC_ARGS"):
        args = string.split(os.environ["RC_ARGS"])
        argv = join_args(args, argv)

    # FIXME: Should support --read-from-file=foo.txt syntax!
    if "--read-from-file" in argv:
        i = argv.index("--read-from-file") + 1
        if i < len(argv):
            filename = argv[i]
            lines = []
            try:
                f = open(filename, "r")
                lines = f.readlines()
            except IOError:
                rctalk.error("Couldn't open file '" + filename + "'")
                sys.exit(1)
            argv = join_args(lines, argv)
        else:
            rctalk.error("No filename provided for --read-from-file option")
            sys.exit(1)

    if "--read-from-stdin" in argv:
        lines = sys.stdin.readlines()
        argv = join_args(lines, argv)

    return argv


###
### The actual RCCommand class
###

class RCCommand:

    def name(self):
        return "Unknown!"

    def aliases(self):
        return []
    
    # If is_hidden returns true, the command will not appear in 'usage'
    # list of available commands.
    def is_hidden(self):
        return 0

    def category(self):
        return "unknown"

    def arguments(self):
        return "..."

    def description_short(self):
        return ""

    def description_long(self):
        return ""

    def default_opt_table(self):
        return default_opt_table

    def local_opt_table(self):
        return []

    def opt_table(self):
        return self.default_opt_table() + self.local_opt_table()


    def default_orthogonal_opts(self):
        return default_orthogonal_opts

    def local_orthogonal_opts(self):
        return []

    def orthogonal_opts(self):
        return self.default_orthogonal_opts() + self.local_orthogonal_opts()


    def usage(self):

        rctalk.message("Usage: rc " + self.name() + " <options> " + \
                       self.arguments())
        rctalk.message("")

        description = self.description_long() or self.description_short()
        if description:
            description = "'" + self.name() + "': " + description
            for l in rcformat.linebreak(description, 72):
                rctalk.message(l)
            rctalk.message("")
        
        opts = self.default_opt_table()
        if opts:
            rctalk.message("General Options:")
            rcformat.opt_table(opts)
            rctalk.message("")

        opts = self.local_opt_table()
        if opts:
            rctalk.message("'" + self.name() + "' Options:")
            rcformat.opt_table(opts)
            rctalk.message("")
        

    def execute(self, server, options_dict, non_option_args):
        rctalk.error("Execute not implemented!")
        sys.exit(1)

    def process_argv(self, argv):
        ###
        ### Expand our synthetic args.
        ### Then compile our list of arguments into something that getopt can
        ### understand.  Finally, call getopt on argv and massage the results
        ### in something easy-to-use.
        ###

        argv = expand_synthetic_args(argv, self.name())

        opt_table = self.opt_table()

        short_opt_getopt = ""
        long_opt_getopt  = []

        short2long_dict = {}

        for o in opt_table:
            
            short_opt = o[0]
            long_opt  = o[1]
            opt_desc  = o[2]

            if short_opt:

                if short2long_dict.has_key(short_opt):
                    rctalk.error("Short option collision!")
                    rctalk.error("-" + short_opt + ", --" + long_opt)
                    rctalk.error("  vs.")
                    rctalk.error("-" + short_opt + ", --" + short2long_dict[short_opt])
                    sys.exit(1)

                short2long_dict[short_opt] = long_opt
                short_opt_getopt = short_opt_getopt + short_opt
                if opt_desc:
                    short_opt_getopt = short_opt_getopt + ":"

            if opt_desc:
                long_opt_getopt.append(long_opt + "=")
            else:
                long_opt_getopt.append(long_opt)

        try:
            optlist, args = getopt.getopt(argv, short_opt_getopt, long_opt_getopt)
        except getopt.error:
            rctalk.error("Unrecognized arguments")
            self.usage()
            sys.exit(1)

        ###
        ### Walk through our list of options and replace short options with the
        ### corresponding long option.
        ###

        i = 0
        while i < len(optlist):
            key = optlist[i][0]
            if key[0:2] != "--":
                optlist[i] = ("--" + short2long_dict[key[1:]], optlist[i][1])
            i = i + 1


        ###
        ### Get the list of "orthogonal" options for this command and, if our
        ### list of options contains orthogonal elements, remove all but the
        ### last such option.
        ### (i.e. if we are handed --quiet --verbose, we drop the --quiet)
        ### 

        optlist.reverse()
        for oo_list in self.orthogonal_opts():
            i = 0
            seen_oo = 0
            while i < len(optlist):
                key = optlist[i][0]
                if key[2:] in oo_list:
                    if seen_oo:
                        del optlist[i]
                        i = i - 1
                    seen_oo = 1
                i = i + 1
        optlist.reverse()

        ###
        ### Store our options in a dictionary
        ###

        opt_dict = {}

        for key, value in optlist:
            opt_dict[key[2:]] = value


        return opt_dict, args



    
    
