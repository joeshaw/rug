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

def get_packages(server, channel):
    return server.rcd.packsys.query([["channel","is",str(channel["id"])]])

def get_system_packages(server):
    return server.rcd.packsys.query([["installed","is","true"]])

def install_indicator(server, package):
    if package["installed"]:
        return "i"
    else:
        return ""

def append_to_table(server, package_table, p, multi):
    row = [install_indicator(server, p),
           str(p["channel"]),
           p["name"],
           rcformat.display_version(p)]

    if multi or rctalk.be_terse:
        package_table.append(row)
    else:
        package_table.append(row[:1]+row[2:])

def sort_and_format_table(package_table, multi):
    header = ["S", "Channel", "Name", "Version"]

    if multi or rctalk.be_terse:
        package_table.sort(lambda x, y:cmp(x[2],y[2]))
        rcformat.tabular(header, package_table)
    else:
        package_table.sort(lambda x, y:cmp(x[1],y[1]))
        rcformat.tabular(header[:1]+header[2:], package_table)

def find_package(server, channel, package):
    if channel != -1:
        [package] = server.rcd.packsys.query([["name",      "is", package],
                                              ["installed", "is", "false"],
                                              ["channel",   "is", channel]])
    else:
        package = server.rcd.packsys.find_latest_version(package)

    return package

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

                clist = rcchannelcmds.get_channels_by_name(server, a)

                if rcchannelcmds.validate_channel_list(a, clist):
                    packages = get_packages(server, clist[0])
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

        if not non_option_args:
            self.usage()
            sys.exit(1)

        multi = 0
        # FIXME: This should support multiple channels
        if options_dict.has_key("channel"):
            if string.lower(options_dict["channel"]) == "all":
                channel = -1
                multi = 1
            else:
                channel = int(options_dict["channel"])
        else:
            channel = 0

        packages = server.rcd.packsys.query([[search_type, "contains", non_option_args[0]]])
        
        # FIXME: Check for -p
        for p in packages:
            if (channel == -1 and p["channel"] != 0) or (channel == p["channel"]):
                append_to_table(server, package_table, p, multi)

        if package_table:
            sort_and_format_table(package_table, multi)
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


class PackageUpdatesCmd(rccommand.RCCommand):

    def name(self):
        return "updates"

    def local_opt_table(self):
        return [["", "sort-by-name", "", "Sort updates by name"],
                ["", "sort-by-channel", "", "Sort updates by channel"]]

    def execute(self, server, options_dict, non_option_args):

        up = server.rcd.packsys.get_updates()

        if non_option_args:
            channel_id_list = []
            failed = 0
            for a in non_option_args:
                clist = rcchannelcmds.get_channels_by_name(server, a)
                if not rcchannelcmds.validate_channel_list(a, clist):
                    failed = 1
                else:
                    channel_id_list.append(clist[0]["id"])
                    
            if failed:
                sys.exit(1)

            up = filter(lambda x, cidl=channel_id_list:x[1]["channel"] in cidl, up)


        table = []

        if options_dict.has_key("sort-by-name"):
            up.sort(lambda x,y:cmp(string.lower(x[1]["name"]),
                                   string.lower(y[1]["name"])))
        elif options_dict.has_key("sort-by-channel"):
            up.sort(lambda x,y:cmp(x[1]["channel"], y[1]["channel"]) \
                    or cmp(string.lower(x[1]["name"]), string.lower(y[1]["name"])))
        else:
            up.sort(lambda x,y:cmp(x[1]["importance_num"], y[1]["importance_num"]) \
                    or cmp(x[1]["channel"], y[1]["channel"]) \
                    or cmp(string.lower(x[1]["name"]), string.lower(y[1]["name"])))
            
        for pair in up:
            old_pkg, new_pkg = pair

            urgency = "?"
            if new_pkg.has_key("importance_str"):
                urgency = new_pkg["importance_str"]
            
            old_ver = str(old_pkg["epoch"]) + "-" + old_pkg["version"] + "-" + old_pkg["release"]
            new_ver = str(new_pkg["epoch"]) + "-" + new_pkg["version"] + "-" + new_pkg["release"]

            chan = rcchannelcmds.get_channel_by_id(server, new_pkg["channel"])

            table.append([urgency,
                          rcchannelcmds.abbrev_channel_name(chan["name"]),
                          new_pkg["name"],
                          old_ver,
                          new_ver])

        if table:
            rcformat.tabular(["Urgency", "Channel", "Name", "Installed Version", "New Version"], table)
        else:
            if non_option_args:
                rctalk.message("No updates are available in the specified channels.")
            else:
                rctalk.message("No updates are available.")
        

rccommand.register(PackageListCmd, "List the packages in a channel")
rccommand.register(PackageSearchCmd, "Search for packages matching criteria")
rccommand.register(PackageInstallCmd, "Install a package")
rccommand.register(PackageUpdatesCmd, "List pending updates")
