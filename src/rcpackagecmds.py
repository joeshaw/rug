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
import time
import rctalk
import rcformat
import rccommand
import rcchannelcmds

def get_packages(server, channel):
    return server.rcd.packsys.search([["channel","is",str(channel["id"])]])

def get_system_packages(server):
    return server.rcd.packsys.search([["installed","is","true"]])

def get_non_system_packages(server):
    return server.rcd.packsys.search([["installed","is","false"]])

def install_indicator(server, package):
    if package["installed"]:
        return "i"
    else:
        return ""

def append_to_table(server, package_table, p, multi, no_abbrev):
    if not p["channel"]:
        channel_name = ""
    else:
        channel_name = rcchannelcmds.channel_id_to_name(server, p["channel"])

    if no_abbrev:
        evr_fn = rcformat.evr_to_str
    else:
        evr_fn = rcformat.evr_to_abbrev_str
        channel_name = rcformat.abbrev_channel_name(channel_name)
        
    row = [install_indicator(server, p),
           channel_name,
           p["name"],
           evr_fn(p)]

    if multi or rctalk.be_terse:
        package_table.append(row)
    else:
        package_table.append(row[:1]+row[2:])

def sort_and_format_table(package_table, multi):
    header = ["S", "Channel", "Name", "Version"]

    if multi or rctalk.be_terse:
        package_table.sort(lambda x, y:cmp(string.lower(x[2]),
                                           string.lower(y[2])) or
                           cmp(string.lower(x[1]),string.lower(y[1])))
        rcformat.tabular(header, package_table)
    else:
        package_table.sort(lambda x, y:cmp(string.lower(x[1]),
                                           string.lower(y[1])))
        rcformat.tabular(header[:1]+header[2:], package_table)

def find_package_in_channel(server, channel, package):
    if channel != -1:
        plist = server.rcd.packsys.search([["name",      "is", package],
                                           ["installed", "is", "false"],
                                           ["channel",   "is", channel]])

        if not plist:
            return None;
        else:
            p = plist[0]
            
        inform = 0
    else:
        p = server.rcd.packsys.find_latest_version(package)
        inform = 1

    return p, inform

def find_package_on_system(server, package):
    plist = server.rcd.packsys.search([["name",      "is", package],
                                       ["installed", "is", "true"]])

    # We need exactly one match
    if not plist or len(plist) > 1:
        return None
    else:
        p = plist[0]

    return p

class PackageListCmd(rccommand.RCCommand):

    def name(self):
        return "packages"

    def local_opt_table(self):
        return [["",  "no-abbrev", "", "Do not abbreviate channel or version information"]]

    def execute(self, server, options_dict, non_option_args):

        packages = [];
        package_table = [];

        no_abbrev = options_dict.has_key("no-abbrev")

        if len(non_option_args) > 1:
            multi = 1
        else:
            multi = 0

        if non_option_args:
            if "all" in non_option_args:
                multi = 1
                packages = get_non_system_packages(server)
                for p in packages:
                    append_to_table(server, package_table, p, multi, no_abbrev)
            else:
                for a in non_option_args:

                    clist = rcchannelcmds.get_channels_by_name(server, a)

                    if rcchannelcmds.validate_channel_list(a, clist):
                        packages = get_packages(server, clist[0])
                        for p in packages:
                            append_to_table(server, package_table, p, multi, no_abbrev)
        else:
            packages = get_system_packages(server)
            for p in packages:
                append_to_table(server, package_table, p, 0, no_abbrev)
            
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
                ["c", "channel", "channel id", "Search in a specific channel"],
                ["",  "no-abbrev", "", "Do not abbreviate channel or version information"]]


    def execute(self, server, options_dict, non_option_args):

        package_table = [];

        no_abbrev = options_dict.has_key("no-abbrev")

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

        packages = server.rcd.packsys.search([[search_type, "contains", non_option_args[0]]])
        
        # FIXME: Check for -p
        for p in packages:
            if (channel == -1 and p["channel"] != 0) or (channel == p["channel"]):
                append_to_table(server, package_table, p, multi, no_abbrev)

        if package_table:
            sort_and_format_table(package_table, multi)
        else:
            rctalk.message("--- No packages found ---")

class PackageUpdatesCmd(rccommand.RCCommand):

    def name(self):
        return "updates"

    def local_opt_table(self):
        return [["", "sort-by-name", "", "Sort updates by name"],
                ["", "sort-by-channel", "", "Sort updates by channel"],
                ["", "no-abbrev", "", "Do not abbreviate channel or version information"]]

    def execute(self, server, options_dict, non_option_args):

        up = server.rcd.packsys.get_updates()

        no_abbrev = options_dict.has_key("no-abbrev") or \
                    options_dict.has_key("terse")

        # Filter out unsubscribed channels
        up = filter(lambda x,s=server:\
                    rcchannelcmds.check_subscription_by_id(s, x[1]["channel"]),
                    up)

        # If channels are specified by the command line, filter out all except
        # for updates from those channels.
        if non_option_args:
            channel_id_list = []
            failed = 0
            for a in non_option_args:
                clist = rcchannelcmds.get_channels_by_name(server, a)
                if not rcchannelcmds.validate_channel_list(a, clist):
                    failed = 1
                else:
                    c = clist[0]
                    if c["subscribed"]:
                        channel_id_list.append(c["id"])
                    else:
                        rctalk.warning("You are not subscribed to "
                                       + rcchannelcmds.channel_to_str(c)
                                       + ", so no updates are available.")
                    
            if failed:
                sys.exit(1)

            up = filter(lambda x, cidl=channel_id_list:x[1]["channel"] in cidl, up)


        table = []

        # Sort our list of updates into some sort of coherent order
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
            old_pkg, new_pkg, descriptions = pair

            urgency = "?"
            if new_pkg.has_key("importance_str"):
                urgency = new_pkg["importance_str"]

            if not no_abbrev:
                urgency = rcformat.abbrev_importance(urgency)

            if no_abbrev:
                evr_fn = rcformat.evr_to_str
            else:
                evr_fn = rcformat.evr_to_abbrev_str

            old_ver = evr_fn(old_pkg)
            new_ver = evr_fn(new_pkg)

            chan = rcchannelcmds.get_channel_by_id(server, new_pkg["channel"])
            chan_name = chan["name"]
            if not no_abbrev:
                chan_name = rcformat.abbrev_channel_name(chan_name)

            table.append([urgency, chan_name, new_pkg["name"], old_ver, new_ver])

        if table:
            rcformat.tabular(["Urg", "Channel", "Name", "Installed", "Update"], table)
        else:
            if non_option_args:
                rctalk.message("No updates are available in the specified channels.")
            else:
                rctalk.message("No updates are available.")

def transact_and_poll(server, packages_to_install, packages_to_remove):
    tid = server.rcd.packsys.transact(packages_to_install, packages_to_remove)
    message_offset = 0
    download_percent = 0.0

    while 1:
        tid_info = server.rcd.system.poll_pending(tid)

        if rctalk.show_verbose and tid_info["percent_complete"] > download_percent:
            download_percent = tid_info["percent_complete"]
            rctalk.message("Download " + str(int(download_percent)) + "% complete")
            
        message_len = len(tid_info["messages"])
            
        if message_len > message_offset:
            for e in tid_info["messages"][message_offset:]:
                rctalk.message(rcformat.transaction_status(e))
            message_offset = message_len
                    
        if tid_info["status"] == "finished" or tid_info["status"] == "failed":
            break

        time.sleep(1)

class PackageInfoCmd(rccommand.RCCommand):

    def name(self):
        return "info"

    def execute(self, server, options_dict, non_option_args):
        for a in non_option_args:
            channel = -1
            package = None

            off = string.find(a, ":")
            if off != -1:
                channel = a[:off]
                package = a[off+1:]
            else:
                package = a

            if channel == -1:
                p = find_package_on_system(server, package)
            else:
                p, inform = find_package_in_channel(server, channel, package)

            if not p:
                rctalk.error("Unable to find package '" + package + "'")
                sys.exit(1)

            pinfo = server.rcd.packsys.package_info(p)

            rctalk.message("Name: " + p["name"])
            rctalk.message("Version: " + p["version"])
            rctalk.message("Release: " + p["release"])
            if pinfo.has_key("file_size"):
                rctalk.message("Package size: 99" + str(pinfo["file_size"]))
            if pinfo.has_key("installed_size"):
                rctalk.message("Installed size: " + str(pinfo["installed_size"]))
            rctalk.message("Summary: " + pinfo["summary"])
            rctalk.message("Description: ")
            rctalk.message("  " + pinfo["description"])

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

            p, inform = find_package_in_channel(server, channel, package)

            if not p:
                rctalk.error("Unable to find package '" + package + "'")
                sys.exit(1)

            if inform:
                rctalk.message("Using " + p["name"] + " " + rcformat.evr_to_str(p) + " from the '" + rcchannelcmds.channel_id_to_name(server, p["channel"]) + "' channel")
                
            packages_to_install.append(p)

        if not packages_to_install:
            rctalk.message("--- No packages to install ---")
            sys.exit(0)

        transact_and_poll(server, packages_to_install, [])

class PackageRemoveCmd(rccommand.RCCommand):

    def name(self):
        return "remove"

    def execute(self, server, options_dict, non_option_args):
        packages_to_remove = []
        
        for a in non_option_args:
            p = find_package_on_system(server, a)

            if not p:
                rctalk.error("Unable to find package '" + a + "'")
                sys.exit(1)
                
            packages_to_remove.append(p)

        if not packages_to_remove:
            rctalk.message("--- No packages to remove ---")
            sys.exit(0)

        transact_and_poll(server, [], packages_to_remove)

rccommand.register(PackageListCmd,    "List the packages in a channel")
rccommand.register(PackageSearchCmd,  "Search for packages matching criteria")
rccommand.register(PackageUpdatesCmd, "List pending updates")
rccommand.register(PackageInfoCmd,    "Show info on a package")
rccommand.register(PackageInstallCmd, "Install a package")
rccommand.register(PackageRemoveCmd,  "Remove a package")
