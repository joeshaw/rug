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
import rctalk
import rcformat
import rccommand
import rcchannelcmds

cached_system_packages = {}

def get_packages(server, channel):
    return server.rcd.packsys.query([["channel","is",str(channel["id"])]])

def get_system_packages(server):
    global cached_system_packages
    if not cached_system_packages:
        system_packages = server.rcd.packsys.query([["installed","is","true"]])
        for a in system_packages:
            cached_system_packages[a["name"]] = a
    else:
        system_packages = cached_system_packages.values();

    return system_packages;

def install_indicator(server, package):
    global cached_system_packages
    if not cached_system_packages:
        get_system_packages(server)

    if cached_system_packages.has_key(package["name"]):
        return "i"
    else:
        return ""

def append_to_table(server, package_table, p, multi):
    row = [install_indicator(server, p),
           str(p["channel"]),
           p["name"],
           rcformat.display_version(p)]

    if multi:
        package_table.append(row)
    else:
        package_table.append(row[:1]+row[2:])

def sort_and_format_table(package_table, multi):
    header = ["S", "Channel", "Name", "Version"]

    if multi:
        package_table.sort(lambda x, y:cmp(x[2],y[2]))
        rcformat.tabular(header, package_table)
    else:
        package_table.sort(lambda x, y:cmp(x[1],y[1]))
        rcformat.tabular(header[:1]+header[2:], package_table)

def find_package(server, channel, package):
    query = [["name", "is", package], ["installed", "is", "false"]]

    if channel != -1:
        query.append(["channel", "is", channel])

    packages = server.rcd.packsys.query(query)

    # FIXME: This is wrong; we should be doing a real version compare here.
    packages.sort(lambda x, y:cmp(rcformat.display_version(y),
                                  rcformat.display_version(x)))

    return packages[0]

class PackageListCmd(rccommand.RCCommand):

    def name(self):
        return "packages"

    def execute(self, server, options_dict, non_option_args):

        packages = [];
        package_table = [];

        if len(non_option_args) > 1:
            multi = 1
        else:
            multi = 0

        if non_option_args:
            for a in non_option_args:
                c = rcchannelcmds.get_channel_by_id(server, a)
                if not c:
                    rctalk.warning("Invalid channel: '" + a + "'")
                else:
                    packages = get_packages(server, c)
                    
                    for p in packages:
                        append_to_table(server, package_table, p, multi)
        else:
            packages = get_system_packages(server)
            for p in packages:
                append_to_table(server, package_table, p, 0)
            
        if package_table:
            sort_and_format_table(package_table, multi)
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
            package_table.append([install_indicator(server, p), str(p["channel"]), p["name"], rcformat.display_version(p)])

        if package_table:
            package_table.sort(lambda x, y:cmp(x[2],y[2]))
            rcformat.tabular(["S", "Channel", "Name", "Version"], package_table)
        else:
            rctalk.message("--- No packages found ---")

class PackageInstallCmd(rccommand.RCCommand):

    def name(self):
        return "install"

    def execute(self, server, options_dict, non_option_args):
        packages_to_install = []
        
        for a in non_option_args:
            channel = -1
            package = None

            off = string.find(a, ":")
            if off != -1:
                channel = a[:off]
                package = a[off+1:]
            else:
                package = a

            p = find_package(server, channel, package)

            if not p:
                rctalk.error("Unable to find package '" + package + "'")
                sys.exit(1)
                
            packages_to_install.append(p)

        if not packages_to_install:
            rctalk.message("--- No packages to install ---")
            sys.exit(0)

        server.rcd.packsys.transact(packages_to_install, [])

rccommand.register(PackageListCmd, "List the packages in a channel")
rccommand.register(PackageSearchCmd, "Search for packages matching criteria")
rccommand.register(PackageInstallCmd, "Install a package")
