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
import rctalk
import rcformat
import rccommand
import rcchannelcmds

cached_system_packages = {}

def get_packages(server, channel):
    return server.rcd.packsys.query([["channel","is",str(channel["id"])]])

def install_indicator(server, package):
    global cached_system_packages
    if not cached_system_packages:
        system_packages = server.rcd.packsys.query([["installed","is","true"]])
        for a in system_packages:
            cached_system_packages[a["name"]] = a

    if cached_system_packages.has_key(package["name"]):
        return "i"
    else:
        return ""

class PackageListCmd(rccommand.RCCommand):

    def name(self):
        return "packages"

    def execute(self, server, options_dict, non_option_args):

        packages = [];
        package_table = [];

        for a in non_option_args:
            c = rcchannelcmds.get_channel_by_id(server, a)
            if not c:
                rctalk.warning("Invalid channel: '" + a + "'")
            else:
                packages = get_packages(server, c);

                for p in packages:
                    package_table.append([install_indicator(server, p), str(p["channel"]), p["name"], p["version"] + "-" + p["release"]])

        if package_table:
            package_table.sort(lambda x, y:cmp(x[2],y[2]))
            rcformat.tabular(["S", "Channel", "Name", "Version"], package_table)
        else:
            rctalk.message("--- No packages found ---")

class PackageSearchCmd(rccommand.RCCommand):

    def name(self):
        return "search"

    def local_opt_table(self):
        return [["n", "search-name", "", "Search name (default)"],
                ["s", "search-summary", "", "Search summary"],
                ["d", "search-description", "", "Search description"],
                ["v", "search-version", "", "Search version"],
                ["u", "search-updates", "", "Search updates"],
                ["p", "show-package-ids", "", "Show package IDs for each package"],
                ["c", "channel", "channel id", "Search in a specific channel"]]

    def execute(self, server, options_dict, non_option_args):

        package_table = [];

        search_type = "name"
        if options_dict.has_key("search-summary"):
            search_type = "summary"
        elif options_dict.has_key("search-description"):
            search_type = "description"
        elif options_dict.has_key("search-version"):
            search_type = "version"
        elif options_dict.has_key("search-updates"):
            search_type = "needs_upgrade"

        # FIXME: Handle -c
        if search_type == "needs_upgrade":
            packages = server.rcd.packsys.query([[search_type, "is", "true"]])
        else:
            if not non_option_args:
                self.usage()
                sys.exit(1)

            packages = server.rcd.packsys.query([[search_type, "contains", non_option_args[0]]])
        
        # FIXME: Check for -p
        for p in packages:
            package_table.append([install_indicator(server, p), str(p["channel"]), p["name"], p["version"] + "-" + p["release"]])

        if package_table:
            package_table.sort(lambda x, y:cmp(x[2],y[2]))
            rcformat.tabular(["S", "Channel", "Name", "Version"], package_table)
        else:
            rctalk.message("--- No packages found ---")

rccommand.register(PackageListCmd, "List the packages in a channel")
rccommand.register(PackageSearchCmd, "Search for packages matching criteria")
