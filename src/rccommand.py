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

def register(constructor, description):
    obj = constructor()
    name = obj.name()
    if command_dict.has_key(name):
        rctalk.error("Command name collision: '"+name+"'")
    else:
        command_dict[name] = (description, constructor)


def construct(name):
    valid_names = command_dict.keys()

    ### Allow partial command names when it is unamiguous
    ### (i.e. "sub" matches "subscribe")
    matches = []
    for n in valid_names:
        if string.find(n, name) == 0:
            matches.append(n)

    if len(matches) == 0:
        rctalk.warning("Unknown command.")
        return None

    if len(matches) > 1:
        rctalk.warning("Ambiguous command")
        rctalk.warning("'"+name+"' matches "+ string.join(matches, ", "))
        sys.exit(1)
        return None
        
    cons = (command_dict[matches[0]])[1]
    return cons()


def usage():
    rctalk.message("Usage: rc <command> <options> ...")
    rctalk.message("")
    rctalk.message("Valid commands are:")
    keys = command_dict.keys()
    if keys:
        keys.sort()
        max_len = apply(max,map(len, keys))
        for k in keys:
            rctalk.message("  " + string.ljust(k, max_len) + "  " + command_dict[k][0])
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


    def default_opt_table(self):
        return default_opt_table;

    def local_opt_table(self):
        return [];

    def opt_table(self):
        return self.default_opt_table() + self.local_opt_table()


    def default_orthogonal_opts(self):
        return default_orthogonal_opts

    def local_orthogonal_opts(self):
        return []

    def orthogonal_opts(self):
        return self.default_orthogonal_opts() + self.local_orthogonal_opts()


    def usage(self):
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

    
    
