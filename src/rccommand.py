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
import string
import rcformat
import rctalk

command_dict = {}
alias_dict = {}

def register(constructor):
    obj = constructor()
    name = obj.name()
    aliases = obj.aliases()
    description = obj.description_short() or "<No Description Available>"

    if command_dict.has_key(name):
        rctalk.error("Command name collision: '"+name+"'")
    else:
        command_dict[name] = (description, constructor, aliases)

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


def usage():
    rctalk.message("Usage: rc <command> <options> ...")
    rctalk.message("")
    rctalk.message("Valid commands are:")
    keys = command_dict.keys()
    if keys:
        keys.sort()
        cmd_list = []
        max_len = apply(max,map(len, keys))
        for k in keys:
            name = k
            description = command_dict[k][0]
            aliases = command_dict[k][2]
            if aliases:
                name = name + " (" + string.join(aliases, ", ") + ")"
            cmd_list.append([name, description])

        max_len = apply(max, map(lambda c:len(c[0]), cmd_list))
        for c in cmd_list:
            rctalk.message("  " + string.ljust(c[0], max_len) + "  " + c[1])
            
    else:
        rctalk.error("<< No commands found --- something is wrong! >>")

default_opt_table = [
    ["U", "user",     "username", "Specify user name"],
    ["P", "password", "password", "Specify password"],
    ["h", "host",     "hostname", "Contact daemon on specified host"],
    ["N", "dry-run",  "",         "Don't perform operation"],
    ["",  "version",  "",         "Print client version and exit"],
    ["V", "verbose",  "",         "Verbose output"],
    ["",  "normal-output", "",    "Normal output (default)"],
    ["t", "terse",    "",         "Terse output"],
    ["",  "quiet",    "",         "Quiet output, print only error messages"],
    ["",  "debug",    "",         "Debugging output"],
    ["",  "batch",    "",         "Run in batch mode"],
    ["",  "read-from-file", "filename",   "Get args from file"],
    ["",  "read-from-stdin", "",  "Get args from stdin"],
    ["",  "ignore-rc-file", "",   "Don't read rc's startup file (~/.rcrc)"],
    ["",  "ignore-env", "",       "Ignore the RC_ARGS environment variable"],
    ["?", "help",     "",         "Get help on a specific command"]
]

default_orthogonal_opts = [["verbose", "terse", "normal-output", "quiet"]]

class RCCommand:

    def name(self):
        return "Unknown!"

    def aliases(self):
        return []

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

    
    
