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
import ximian_xmlrpclib

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
            return None
        else:
            p = plist[0]
            
        inform = 0
    else:
        try:
            p = server.rcd.packsys.find_latest_version(package)
        except ximian_xmlrpclib.Fault, f:
            if f.faultCode == -601:
                p = None
            else:
                raise
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

def get_updates(server, non_option_args):
    up = server.rcd.packsys.get_updates()

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

    return up

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

class PackagesCmd(rccommand.RCCommand):

    def name(self):
        return "frobnicate"

    def local_opt_table(self):
        return [["", "match-all", "",              "Require packages to match all search strings (default)"],
                ["", "match-any", "",              "Allow packages to match any search string"],
                ["", "match-substrings", "",       "Match search strings against any part of the text"],
                ["", "match-words",      "",       "Require search strings to match entire words"],
                ["", "search-description", "",     "Look for search strings in package descriptions"],
                ["", "installed-only",   "",       "Only show installed packages"],
                ["", "uninstalled-only", "",       "Only show uninstalled packages"],
                ["", "channel",         "channel", "Show packages from one specific channel"],
                ["", "show-package-ids",   "",     "Show package IDs"],
                ["", "no-abbrev", "",              "Don't abbreviate channel or version information"]]

    def local_orthogonal_opts(self):
        return [["match-any", "match-all"],
                ["match-substrings", "match-words"],
                ["installed-only", "uninstalled-only"]]

    def execute(self, server, options_dict, non_option_args):

        if options_dict.has_key("search-descriptions"):
            key = "name" ## should be name_or_desc
        else:
            key = "name"

        if options_dict.has_key("match-words"):
            op = "contains_word"
        else:
            op = "contains"

        query = []
        for s in non_option_args:
            query.append([key, op, s])

        if query and options_dict.has_key("match-any"):
            query.insert(0, ["", "begin-or", ""])
            query.append(["", "end-or", ""])

        if options_dict.has_key("installed-only"):
            query.append(["installed", "=", "true"])
        elif options_dict.has_key("uninstalled-only"):
            query.append(["installed", "=", "false"])

        if options_dict.has_key("channel"):
            cname = options_dict["channel"]
            clist = rcchannelcmds.get_channels_by_name(server,cname)
            if not rcchannelcmds.validate_channel_list(cname, clist):
                sys.exit(1)
            c = clist[0]

            query.append(["channel", "=", str(c["id"])])

        packages = server.rcd.packsys.search(query)

        package_table = []
        no_abbrev = options_dict.has_key("no-abbrev")
        
        for p in packages:
            append_to_table(server, package_table, p, 1, no_abbrev)

        if package_table:
            sort_and_format_table(package_table, 1)
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
                ["i",  "installed-only", "", "List installed packages only"],
                ["u",  "uninstalled-only", "", "List uninstalled packages only"],
                ["",  "no-abbrev", "", "Do not abbreviate channel or version information"]]


    def execute(self, server, options_dict, non_option_args):

        package_table = []
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

        if options_dict.has_key("installed-only"):
            packages = filter(lambda x:x["installed"], packages)

        if options_dict.has_key("uninstalled-only"):
            packages = filter(lambda x:not x["installed"], packages)
        
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

        no_abbrev = options_dict.has_key("no-abbrev") or \
                    options_dict.has_key("terse")

        up = get_updates(server, non_option_args)

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

def transact_and_poll(server, packages_to_install, packages_to_remove):
    tid = server.rcd.packsys.transact(packages_to_install, packages_to_remove)
    message_offset = 0
    download_percent = 0.0

    while 1:
        tid_info = None

        try:
            tid_info = server.rcd.system.poll_pending(tid)
            
            if tid_info["percent_complete"] > download_percent:
                download_percent = tid_info["percent_complete"]
                progress_msg = "Download " + rcformat.pending_to_str(tid_info)
                rctalk.message_status(progress_msg)

            if tid_info["status"] != "running":
                rctalk.message_finished("Download complete")

            message_len = len(tid_info["messages"])

            if message_len > message_offset:
                for e in tid_info["messages"][message_offset:]:
                    rctalk.message(rcformat.transaction_status(e))
                message_offset = message_len

            if tid_info["status"] == "finished" or tid_info["status"] == "failed":
                break

            time.sleep(1)
        except KeyboardInterrupt:
            if tid_info and tid_info["status"] == "running":
                rctalk.message("Aborting download...")
                v = server.rcd.packsys.abort_download(tid)
                print "Abort: " + str(v)
                if v:
                    sys.exit(0)
            elif tid_info:
                rctalk.warning("Transaction cannot be aborted")

def format_dependencies(dep_list):
    dep_list.sort(lambda x,y:cmp(string.lower(x["name"]),
                                 string.lower(y["name"])))
    plist = ""
    for p in dep_list:
        plist = plist + " " + p["name"]
    map(lambda x:rctalk.message("  " + x), rcformat.linebreak(plist, 72))

class PackageInstallCmd(rccommand.RCCommand):

    def name(self):
        return "install"

    def local_opt_table(self):
        return [["d", "allow-removals", "", "Allow removals with no confirmation"],
                ["y", "no-confirmation", "", "Perform the actions without confirmation"]]

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

        dep_install, dep_remove = server.rcd.packsys.resolve_dependencies(packages_to_install, [])

        if rctalk.show_verbose:
            rctalk.message("The following requested packages will be installed:")
            format_dependencies(packages_to_install)

        if dep_install:
            rctalk.message("The following additional packages will be installed:")
            format_dependencies(dep_install)

        if dep_remove:
            rctalk.message("The following packages must be REMOVED:")
            format_dependencies(dep_remove)

        if not options_dict.has_key("no-confirmation") and (dep_install or dep_remove):
            confirm = raw_input("Do you want to continue? [Y/n] ")
            if confirm and not (confirm[0] == "y" or confirm[0] == "Y"):
                rctalk.message("Aborted.")
                sys.exit(0)

        if options_dict.has_key("no-confirmation") and not options_dict.has_key("allow-removals"):
            rctalk.warning("Removals are required.  Use the -d option or confirm interactively.")
            sys.exit(1)

        transact_and_poll(server, packages_to_install + dep_install, dep_remove)

class PackageRemoveCmd(rccommand.RCCommand):

    def name(self):
        return "remove"

    def local_opt_table(self):
        return [["y", "no-confirmation", "", "Perform the actions without confirmation"]]

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

        dep_install, dep_remove = server.rcd.packsys.resolve_dependencies([], packages_to_remove)

        if rctalk.show_verbose:
            rctalk.message("The following requested packages will be REMOVED:")
            format_dependencies(packages_to_remove)

        if dep_install:
            rctalk.message("The following additional packages will be installed:")
            format_dependencies(dep_install)

        if dep_remove:
            rctalk.message("The following packages must also be REMOVED:")
            format_dependencies(dep_remove)

        if not options_dict.has_key("no-confirmation") and (dep_install or dep_remove):
            confirm = raw_input("Do you want to continue? [Y/n] ")
            if confirm and not (confirm[0] == "y" or confirm[0] == "Y"):
                rctalk.message("Aborted.")
                sys.exit(0)

        transact_and_poll(server, dep_install, packages_to_remove + dep_remove)

class PackageUpdateCmd(rccommand.RCCommand):

    def name(self):
        return "update-all"

    def local_opt_table(self):
        return [["d", "allow-removals", "", "Allow removals with no confirmation"],
                ["y", "no-confirmation", "", "Perform the actions without confirmation"]]

    def execute(self, server, options_dict, non_option_args):
        up = get_updates(server, non_option_args)

        # x[1] is the package to be updated
        packages_to_install = map(lambda x:x[1], up)

        if not packages_to_install:
            rctalk.message("--- No packages to update ---")
            sys.exit(0)

        dep_install, dep_remove = server.rcd.packsys.resolve_dependencies(packages_to_install, [])

        rctalk.message("The following packages will be updated:")
        format_dependencies(packages_to_install)

        if dep_install:
            rctalk.message("The following additional packages will be installed:")
            format_dependencies(dep_install)

        if dep_remove:
            rctalk.message("The following packages must be REMOVED:")
            format_dependencies(dep_remove)

        if not options_dict.has_key("no-confirmation") and (dep_install or dep_remove):
            confirm = raw_input("Do you want to continue? [Y/n] ")
            if confirm and not (confirm[0] == "y" or confirm[0] == "Y"):
                rctalk.message("Aborted.")
                sys.exit(0)

        if options_dict.has_key("no-confirmation") and not options_dict.has_key("allow-removals"):
            rctalk.warning("Removals are required.  Use the -d option or confirm interactively.")
            sys.exit(1)

        transact_and_poll(server, packages_to_install + dep_install, dep_remove)

rccommand.register(PackageListCmd,    "List the packages in a channel")
rccommand.register(PackageSearchCmd,  "Search for packages matching criteria")

rccommand.register(PackagesCmd,       "Experimental searching command")

rccommand.register(PackageUpdatesCmd, "List pending updates")
rccommand.register(PackageInfoCmd,    "Show info on a package")
rccommand.register(PackageInstallCmd, "Install a package")
rccommand.register(PackageRemoveCmd,  "Remove a package")
rccommand.register(PackageUpdateCmd,  "Update all available packages")
