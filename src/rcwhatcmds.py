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

import os
import sys
import string
import rctalk
import rcformat
import rcchannelutils
import rccommand


def dep_table(server, pairs, dep_name, by_channel = 0, no_abbrev = 0):

    if not pairs:
        rctalk.message("--- No matches ---")
        sys.exit(0)

    table = []

    if no_abbrev:
        evr_fn = rcformat.evr_to_str
    else:
        evr_fn = rcformat.evr_to_abbrev_str

    pkg_dict = {}
    
    for pkg, dep in pairs:

        if pkg["installed"]:
            installed = "i"
        else:
            installed = ""

        pkg_name = pkg["name"]
        pkg_evr = evr_fn(pkg)

        if pkg.has_key("channel_guess"):
            id = pkg["channel_guess"]
        else:
            id = pkg["channel"]
        channel = rcchannelutils.channel_id_to_name(server, id)
        if not no_abbrev:
            channel = rcformat.abbrev_channel_name(channel)

        if dep.has_key("relation"):
            dep_str = dep["relation"] + " " + evr_fn(dep)
        else:
            dep_str = evr_fn(dep)

        # We check pkg_dict to avoid duplicates between the installed
        # and in-channel version of packages.
        key = pkg_name + "||" + pkg_evr + "||" + dep_str
        if not pkg_dict.has_key(key):
            row = [installed, channel, pkg_name, pkg_evr, dep_str]
            table.append(row)
            pkg_dict[key] = 1

    if by_channel:
        sort_fn = lambda x,y:cmp(string.lower(x[1]), string.lower(y[1])) or \
                  cmp(string.lower(x[2]), string.lower(y[2]))
    else:
        sort_fn = lambda x,y:cmp(string.lower(x[2]), string.lower(y[2])) or \
                  cmp(string.lower(x[1]), string.lower(y[1]))

    table.sort(sort_fn)

    rcformat.tabular(["S", "Channel", "Package", "Version", dep_name + " Version"], table)




###
### Common base class

class WhateverCmd(rccommand.RCCommand):

    def arguments(self):
        return "<package-dep>"

    def local_opt_table(self):
        return [["",  "no-abbrev", "", "Do not abbreviate channel or version information"],
                ["i", "installed-only", "", "Show installed packages only"],
                ["u", "uninstalled-only", "", "Show uninstalled packages only"],
                ["",  "sort-by-name", "", "Sort packages by name (default)"],
                ["",  "sort-by-channel", "", "Sort packages by channel"]]

    def local_orthogonal_opts(self):
        return [["installed-only", "uninstalled-only"],
                ["sort-by-name", "sort-by-channel"]]


    def execute(self, server, options_dict, non_option_args):
        
        dep_name = non_option_args[0]

        dep = {}
        dep["name"] = dep_name
        dep["relation"] = "(any)"
        dep["has_epoch"] = 0
        dep["epoch"] = 0
        dep["version"] = "foo"
        dep["release"] = "bar"

        what = self.query_fn(server)(dep)

        if options_dict.has_key("installed-only"):
            what = filter(lambda p:p[0]["installed"], what)
        elif options_dict.has_key("uninstalled-only"):
            what = filter(lambda p:not p[0]["installed"], what)
        
        dep_table(server, what, dep_name,
                  options_dict.has_key("sort-by-channel"),
                  options_dict.has_key("no-abbrev"))

        

###
### "what-provides" command
###

class WhatProvidesCmd(WhateverCmd):

    def name(self):
        return "what-provides"

    def aliases(self):
        return ["prov"]

    def description_short(self):
        return "List packages that provide the item you specify"

    def query_fn(self, server):
        return server.rcd.packsys.what_provides


###
### "what-requires" command
###

class WhatRequiresCmd(WhateverCmd):

    def name(self):
        return "what-requires"

    def aliases(self):
        return ["req"]

    def description_short(self):
        return "List packages that require the item you specify"

    def query_fn(self, server):
        return server.rcd.packsys.what_requires
    

###
### "what-conflicts" command
###

class WhatConflictsCmd(WhateverCmd):

    def name(self):
        return "what-conflicts"

    def aliases(self):
        return ["conf"]

    def description_short(self):
        return "List packages that conflict with the item you specify"

    def query_fn(self, server):
        return server.rcd.packsys.what_conflicts
    

rccommand.register(WhatProvidesCmd)
rccommand.register(WhatRequiresCmd)
rccommand.register(WhatConflictsCmd)
