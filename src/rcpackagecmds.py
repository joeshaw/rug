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

import errno
import os
import sys
import string
import time
import zlib

import rctalk
import rcformat
import rccommand
import rcchannelutils
import rcmain
import ximian_xmlrpclib

def find_package_in_channel(server, channel, package, allow_unsub):
    if channel != -1:
        plist = server.rcd.packsys.search([["name",      "is", package],
                                           ["installed", "is", "false"],
                                           ["channel",   "is", str(channel)]])

        if not plist:
            return (None, 0)
        else:
            p = plist[0]
            
        inform = 0
    else:
        try:
            if allow_unsub:
                b = ximian_xmlrpclib.False
            else:
                b = ximian_xmlrpclib.True
            
            p = server.rcd.packsys.find_latest_version(package, b)
        except ximian_xmlrpclib.Fault, f:
            if f.faultCode == -601:
                p = None
            else:
                raise

        if p:
            inform = 1
        else:
            inform = 0

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

def find_local_package(server, package):
    try:
        os.stat(package)
    except OSError, e:
        eno, estr = e
        if eno == errno.ENOENT:
            # No such file or directory.
            return None
        else:
            raise

    try:
        server.rcd.packsys.query_file(package)
    except ximian_xmlrpclib.Fault, f:
        if f.faultCode == -613:
            return None
        else:
            raise

    if rcmain.local:
        return package
    else:
        return ximian_xmlrpclib.Binary(open(package).read())

def get_updates(server, non_option_args):
    up = server.rcd.packsys.get_updates()

    # If channels are specified by the command line, filter out all except
    # for updates from those channels.
    if non_option_args:
        channel_id_list = []
        failed = 0
        for a in non_option_args:
            clist = rcchannelutils.get_channels_by_name(server, a)
            if not rcchannelutils.validate_channel_list(a, clist):
                failed = 1
            else:
                c = clist[0]
                if c["subscribed"]:
                    channel_id_list.append(c["id"])
                else:
                    rctalk.warning("You are not subscribed to "
                                   + rcchannelutils.channel_to_str(c)
                                   + ", so no updates are available.")
                    
        if failed:
            sys.exit(1)

        up = filter(lambda x, cidl=channel_id_list:x[1]["channel"] in cidl, up)

    return up

###
### "packages" command
###

class PackagesCmd(rccommand.RCCommand):

    def name(self):
        return "packages"

    def arguments(self):
        return "<channel> <channel> ..."

    def description_short(self):
        return "List the packages in a channel"

    def local_opt_table(self):
        return [["", "no-abbrev", "", "Do not abbreviate channel or version information"],
                ["", "sort-by-name", "", "Sort packages by name (default)"],
                ["", "sort-by-channel", "", "Sort packages by channel"]]

    def execute(self, server, options_dict, non_option_args):

        packages = []
        package_table = []

        multiple_channels = 1

        query = []
        if non_option_args:
            for a in non_option_args:

                    clist = rcchannelutils.get_channels_by_name(server, a)

                    if rcchannelutils.validate_channel_list(a, clist):
                        query = map(lambda c:["channel", "=", str(c["id"])], clist)
                        if len(query) > 1:
                            query.insert(0, ["", "begin-or", ""])
                            query.append(["", "end-or", ""])

                    if len(clist) == 1:
                        multiple_channels = 0

        else:
            query = [["installed", "=", "true"]]

        packages = server.rcd.packsys.search(query)

        if options_dict.has_key("sort-by-channel"):
            for p in packages:
                rcchannelutils.add_channel_name(server, p)

            packages.sort(lambda x,y:cmp(string.lower(x["channel_name"]), string.lower(y["channel_name"])) \
                          or cmp(string.lower(x["name"]), string.lower(y["name"])))
        else:
            packages.sort(lambda x,y:cmp(string.lower(x["name"]),string.lower(y["name"])))

        if multiple_channels:
            keys = ["installed", "channel", "name", "version"]
            headers = ["S", "Channel", "Name", "Version"]
        else:
            keys = ["installed", "name", "version"]
            headers = ["S", "Name", "Version"]

        
        for p in packages:
            row = rcformat.package_to_row(server, p, options_dict.has_key("no-abbrev"), keys)
            package_table.append(row)

            
        if package_table:
            rcformat.tabular(headers, package_table)
        else:
            rctalk.message("--- No packages found ---")





###
### "search" command
###

def pkg_to_key(p):
    return p["name"]+":"+str(p["epoch"])+":"+p["version"]+":"+p["release"]

class PackageSearchCmd(rccommand.RCCommand):

    def name(self):
        return "search"

    def arguments(self):
        return "<search-string> <search-string>..."

    def description_short(self):
        return "Search for a package"
        
    def local_opt_table(self):
        return [["", "match-all", "",              "Require packages to match all search strings (default)"],
                ["", "match-any", "",              "Allow packages to match any of the search strings"],
                ["", "match-substrings", "",       "Match search strings against any part of the text"],
                ["", "match-words",      "",       "Require search strings to match entire words"],
                ["", "search-description", "",     "Search only in the descriptions of packages and not their names"],
                ["i", "installed-only",   "",      "Show only packages that are already installed"],
                ["u", "uninstalled-only", "",      "Show only packages that are not currently installed"],
                ["c", "channel",        "channel", "Show only the packages from the channel you specify"],
                ["", "show-package-ids",   "",     "Show package IDs"],
                ["", "sort-by-name",     "",       "Sort packages by name (default)"],
                ["", "sort-by-channel",  "",       "Sort packages by channel"],
                ["", "no-abbrev", "",              "Don't abbreviate channel or version information"]]

    def local_orthogonal_opts(self):
        return [["match-any", "match-all"],
                ["match-substrings", "match-words"],
                ["installed-only", "uninstalled-only"]]

    def execute(self, server, options_dict, non_option_args):

        if options_dict.has_key("search-descriptions"):
            key = "text"
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
            clist = rcchannelutils.get_channels_by_name(server,cname)
            if not rcchannelutils.validate_channel_list(cname, clist):
                sys.exit(1)
            c = clist[0]

            query.append(["channel", "=", str(c["id"])])

        packages = server.rcd.packsys.search(query)

        # Keep track of all of the installed packages where
        # we know that it comes from a certain channel.
        # (It doesn't matter if we are doing a channel search,
        # so we leave our dict empty in that case.)x
        in_channel = {}
        if not options_dict.has_key("channel"):
            for p in packages:
                if p["channel"] and p["installed"]:
                    in_channel[pkg_to_key(p)] = 1

        package_table = []
        no_abbrev = options_dict.has_key("no-abbrev")

        for p in packages:
            if p["channel"] != 0 or not in_channel.has_key(pkg_to_key(p)):
                row = rcformat.package_to_row(server, p, no_abbrev,
                                              ["installed", "channel", "name", "version"])
                package_table.append(row)

        if package_table:
            
            if options_dict.has_key("sort-by-channel"):
                package_table.sort(lambda x,y:cmp(string.lower(x[1]), string.lower(y[1])) or\
                                   cmp(string.lower(x[2]), string.lower(y[2])))
            else:
                package_table.sort(lambda x,y:cmp(string.lower(x[2]), string.lower(y[2])))
                
            rcformat.tabular(["S", "Channel", "Name", "Version"], package_table)
        else:
            rctalk.message("--- No packages found ---")



###
### "updates" command
###

def terse_updates_table(server, update_list):

    update_table = []

    for update_item in update_list:

        old_pkg, new_pkg, descriptions = update_item

        urgency = "?"
        if new_pkg.has_key("importance_str"):
            urgency = new_pkg["importance_str"]

        channel_name = rcchannelutils.channel_id_to_name(server, new_pkg["channel"])

        old_ver = rcformat.evr_to_str(old_pkg)
        new_ver = rcformat.evr_to_str(new_pkg)

        update_table.append([urgency, channel_name, new_pkg["name"], old_ver, new_ver])


    update_table.sort(lambda x,y:cmp(string.lower(x[1]), string.lower(y[1])) or \
                      cmp(string.lower(x[2]), string.lower(y[2])))

    rcformat.tabular([], update_table)
    

def exploded_updates_table(server, update_list, no_abbrev):

    channel_name_dict = {}

    for update_item in update_list:
        ch = update_item[1]["channel"]
        if not channel_name_dict.has_key(ch):
            channel_name_dict[ch] = rcchannelutils.channel_id_to_name(server, ch)

    update_list.sort(lambda x,y,cnd=channel_name_dict:\
                     cmp(string.lower(cnd[x[1]["channel"]]),
                         string.lower(cnd[y[1]["channel"]])) \
                     or cmp(x[1]["importance_num"], y[1]["importance_num"]) \
                     or cmp(string.lower(x[1]["name"]), string.lower(y[1]["name"])))

    if no_abbrev:
        evr_fn = rcformat.evr_to_str
    else:
        evr_fn = rcformat.evr_to_abbrev_str

    this_channel_table = []
    this_channel_id = -1

    # An ugly hack
    update_list.append(("", {"channel":"last"}, ""))

    for update_item in update_list:

        old_pkg, new_pkg, descriptions = update_item

        chan_id = new_pkg["channel"]
        if chan_id != this_channel_id or chan_id == "last":
            if this_channel_table:
                rctalk.message("")

                channel_name = channel_name_dict[this_channel_id]
                rctalk.message("Updates for channel '" + channel_name + "'")
                
                rcformat.tabular(["Urg", "Name", "Current Version", "Update Version"],
                                 this_channel_table)

            if chan_id == "last":
                break

            this_channel_table = []
            this_channel_id = chan_id

        urgency = "?"
        if new_pkg.has_key("importance_str"):
            urgency = new_pkg["importance_str"]
            if not no_abbrev:
                urgency = rcformat.abbrev_importance(urgency)

        old_ver = evr_fn(old_pkg)
        new_ver = evr_fn(new_pkg)

        this_channel_table.append([urgency, new_pkg["name"], old_ver, new_ver])


def verbose_updates_list(server, update_list):

    update_list.sort(lambda x, y:cmp(x[1]["importance_num"], y[1]["importance_num"]) \
                     or cmp(string.lower(x[1]["name"]), string.lower(y[1]["name"])))

    for update_item in update_list:

        old_pkg, new_pkg, descriptions = update_item

        ch = rcchannelutils.get_channel_by_id(server, new_pkg["channel"])
        
        rctalk.message("        Name: " + new_pkg["name"])
        rctalk.message("     Channel: " + ch["name"])
        rctalk.message("     Urgency: " + new_pkg["importance_str"])
        rctalk.message("Current Vers: " + rcformat.evr_to_str(old_pkg))
        rctalk.message(" Update Vers: " + rcformat.evr_to_str(new_pkg))

        header = "Enhancements: "
        for d in descriptions:
            rctalk.message(header + d)
            header = "              "

        rctalk.message("")
        

class PackageUpdatesCmd(rccommand.RCCommand):

    def name(self):
        return "updates"

    def aliases(self):
        return ["up"]

    def arguments(self):
        return "<channel> <channel> ..."

    def description_short(self):
        return "List available updates"

    def local_opt_table(self):
        return [["", "sort-by-name", "", "Sort updates by name"],
                ["", "sort-by-channel", "", "Sort updates by channel"],
                ["", "no-abbrev", "", "Do not abbreviate channel or version information"]]

    def execute(self, server, options_dict, non_option_args):

        no_abbrev = options_dict.has_key("no-abbrev") or \
                    options_dict.has_key("terse")

        up = get_updates(server, non_option_args)

        if not up:
            if non_option_args:
                rctalk.message("No updates are available in the specified channels.")
            else:
                rctalk.message("No updates are available.")
            sys.exit(0)

        if rctalk.show_verbose:
            verbose_updates_list(server, up)
        elif rctalk.be_terse:
            terse_updates_table(server, up)
        else:
            exploded_updates_table(server, up, no_abbrev)


###
### "summary" command
###

class SummaryCmd(rccommand.RCCommand):

    def name(self):
        return "summary"

    def aliases(self):
        return ["sum"]

    def arguments(self):
        return ""

    def description_short(self):
        return "Display a summary of available updates"

    def local_opt_table(self):
        return [["", "no-abbrev", "", "Don't abbreviate channel names or importance levels"]]

    def execute(self, server, options_dict, non_option_args):

        no_abbrev = options_dict.has_key("no-abbrev")

        update_list = get_updates(server, [])

        if not update_list:
            rctalk.message("There are no available updates at this time.")
            sys.exit(0)

        count = len(update_list)
        necessary_count = 0
        urgent_count = 0

        seen_channels = {}
        seen_importance = {}
        tally = {}
        tally_by_urgency = {}

        for update_item in update_list:

            old_pkg, new_pkg, descriptions = update_item

            imp = new_pkg["importance_str"]

            if imp == "necessary":
                necessary_count = necessary_count + 1
            if imp == "urgent":
                urgent_count = urgent_count + 1

            ch = rcchannelutils.channel_id_to_name(server, new_pkg["channel"])
            seen_channels[ch] = 1

            seen_importance[imp] = new_pkg["importance_num"]

            key = ch + "||" + imp
            if tally.has_key(key):
                tally[key] = tally[key] + 1
            else:
                tally[key] = 1

            if tally_by_urgency.has_key(imp):
                tally_by_urgency[imp] = tally_by_urgency[imp] + 1
            else:
                tally_by_urgency[imp] = 1

        rctalk.message("")


        rctalk.message("There %s %d update%s available at this time." \
                       % ((count != 1 and "are") or "is", count, (count != 1 and "") or "s"))

        if necessary_count:
            rctalk.message("%d update%s marked as 'necessary'." \
                           % (necessary_count, (necessary_count != 1 and "s are") or " is"))

        if urgent_count:
            rctalk.message("%d update%s marked as 'urgent'." \
                           % (urgent_count, (urgent_count != 1 and "s are") or " is"))

        rctalk.message("")

        channels = seen_channels.keys()
        channels.sort(lambda x,y:cmp(string.lower(x), string.lower(y)))

        importances = seen_importance.keys()
        importances.sort(lambda x,y,f=seen_importance:cmp(f[x], f[y]))

        header = ["Channel"]
        if no_abbrev or len(importances) <= 4:
            header = header + importances
        else:
            header = header + map(rcformat.abbrev_importance, importances)
        header = header + ["total"]
        
        table = []

        for ch in channels:

            if no_abbrev:
                row = [ch]
            else:
                row = [rcformat.abbrev_channel_name(ch)]

            row_count = 0
            
            for imp in importances:
                key = ch + "||" + imp
                if tally.has_key(key):
                    row.append(string.rjust(str(tally[key]), 3))
                    row_count = row_count + tally[key]
                else:
                    row.append("")

            if count:
                row.append(string.rjust(str(row_count), 3))
            else:
                row.append("")
                
            table.append(row)

        row = ["total"]
        for imp in importances:
            row.append(string.rjust(str(tally_by_urgency[imp]), 3))
        row.append(string.rjust(str(count), 3))

        table.append(row)

        rcformat.tabular(header, table)

        rctalk.message("")

        
            

###
### "info" command
###

class PackageInfoCmd(rccommand.RCCommand):

    def name(self):
        return "info"

    def arguments(self):
        return "<package-name>"

    def description_short(self):
        return "Show detailed information about a package"

    def local_opt_table(self):
        return [["u", "allow-unsubscribed", "", "Search in unsubscribed channels as well"]]

    def execute(self, server, options_dict, non_option_args):

        if options_dict.has_key("allow-unsubscribed"):
            allow_unsub = 1
        else:
            allow_unsub = 0

        for a in non_option_args:
            channel = None
            package = None

            off = string.find(a, ":")
            if off != -1:
                channel = a[:off]
                package = a[off+1:]
            else:
                package = a

            if not channel:
                p = find_package_on_system(server, package)

                if not p:
                    p, inform = find_package_in_channel(server, -1, package, allow_unsub)

                    if inform:
                        rctalk.message("Using " + p["name"] + " " +
                                       rcformat.evr_to_str(p) + " from the '" +
                                       rcchannelutils.channel_id_to_name(server, p["channel"]) +
                                       "' channel")

            else:
                clist = rcchannelutils.get_channels_by_name(server, channel)
                if not rcchannelutils.validate_channel_list(channel, clist):
                    sys.exit(1)

                c = clist[0]
                p, inform = find_package_in_channel(server, c["id"], package, allow_unsub)

            if not p:
                if allow_unsub:
                    rctalk.error("Unable to find package '" + package + "' in any subscribed channel")
                else:
                    rctalk.error("Unable to find package '" + package + "'")
                sys.exit(1)

            pinfo = server.rcd.packsys.package_info(p)

            rctalk.message("")
            rctalk.message("Name: " + p["name"])
            rctalk.message("Version: " + p["version"])
            rctalk.message("Release: " + p["release"])
            if pinfo.has_key("file_size"):
                rctalk.message("Package size: " + str(pinfo["file_size"]))
            if pinfo.has_key("installed_size"):
                rctalk.message("Installed size: " + str(pinfo["installed_size"]))
            rctalk.message("Summary: " + pinfo["summary"])
            rctalk.message("Description: ")
            rctalk.message(pinfo["description"])

            log_entries = server.rcd.log.query_log([["name", "=", p["name"]]])
            if log_entries:

                # Reverse chronological order
                log_entries.sort(lambda x,y:cmp(y["timestamp"], x["timestamp"]))

                act_len_list = map(lambda x:len(x["action"]), log_entries)
                if len(act_len_list) > 1:
                    act_len = apply(max, act_len_list)
                else:
                    act_len = act_len_list[0]
                
                rctalk.message("\nHistory:")
                                
                for item in log_entries:

                    init_str = ""
                    fin_str = ""

                    if item.has_key("pkg_initial"):
                        init_str = rcformat.evr_to_abbrev_str(item["pkg_initial"])
                    if item.has_key("pkg_final"):
                        fin_str = rcformat.evr_to_abbrev_str(item["pkg_final"])

                    if init_str and fin_str:
                        pkg_str = init_str + " => " + fin_str
                    elif init_str:
                        pkg_str = init_str
                    elif fin_str:
                        pkg_str = fin_str

                    time_str = time.strftime("%Y-%m-%d %H:%M,",
                                             time.localtime(item["timestamp"]))

                    action_str = string.ljust(item["action"] + ",", act_len+1)

                    if pkg_str:
                        rctalk.message(time_str + " " + action_str + " " + pkg_str)

def transact_and_poll(server, packages_to_install, packages_to_remove, dry_run):
    tid = server.rcd.packsys.transact(packages_to_install,
                                      packages_to_remove,
                                      ximian_xmlrpclib.Boolean(dry_run))
    message_offset = 0
    download_percent = 0.0

    while 1:
        tid_info = None

        try:
            tid_info = server.rcd.system.poll_pending(tid)
            
            if tid_info["percent_complete"] > download_percent:
                download_percent = tid_info["percent_complete"]
                progress_msg = rcformat.pending_to_str(tid_info)
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

            time.sleep(0.4)
        except KeyboardInterrupt:
            if tid_info and tid_info["status"] == "running":
                rctalk.message("")
                rctalk.message("Aborting download...")
                v = server.rcd.packsys.abort_download(tid)
                if v:
                    sys.exit(0)
                else:
                    rctalk.warning("Transaction cannot be aborted")
            elif tid_info:
                rctalk.warning("Transaction cannot be aborted")

def extract_package(dep_or_package):
    # Check to see if we're dealing with package op structures or real
    # package structures.  Package structures won't have a "package" key.

    if dep_or_package.has_key("package"):
        return dep_or_package["package"]
    else:
        return dep_or_package

def extract_packages(dep_or_package_list):
    return map(lambda x:extract_package(x), dep_or_package_list)

def format_dependencies(server, dep_list):
    dep_list.sort(lambda x,y:cmp(string.lower(extract_package(x)["name"]),
                                 string.lower(extract_package(y)["name"])))

    dlist = []
    for d in dep_list:
        p = extract_package(d)

        c = rcchannelutils.channel_id_to_name(server, p["channel"])
        if c:
            c = "(" + c + ")"
        else:
            c = ""

        rctalk.message("  " + p["name"] + " " + rcformat.evr_to_str(p) +
                       " " + c)

        if d.has_key("details"):
            map(lambda x:rctalk.message("    " + x), d["details"])

    rctalk.message("")

###
### "install" command
###

class PackageInstallCmd(rccommand.RCCommand):

    def name(self):
        return "install"

    def arguments(self):
        return "<package-name> <package-name> ..."

    def description_short(self):
        return "Install packages"

    def local_opt_table(self):
        return [["d", "allow-removals", "", "Permit removal of software without confirmation"],
                ["y", "no-confirmation", "", "Permit all actions without confirmations"],
                ["u", "allow-unsubscribed", "", "Include unsubscribed channels when searching for software"]]

    def execute(self, server, options_dict, non_option_args):
        packages_to_install = []
        
        if options_dict.has_key("allow-unsubscribed"):
            allow_unsub = 1
        else:
            allow_unsub = 0

        if options_dict.has_key("dry-run"):
            dry_run = 1
        else:
            dry_run = 0

        for a in non_option_args:
            channel = None
            package = None

            off = string.find(a, ":")
            if off != -1:
                channel = a[:off]
                package = a[off+1:]
            else:
                package = a

            if not channel:
                c = -1
            else:
                clist = rcchannelutils.get_channels_by_name(server, channel)
                if not rcchannelutils.validate_channel_list(channel, clist):
                    sys.exit(1)
                c = clist[0]["id"]
            
            p, inform = find_package_in_channel(server, c, package, allow_unsub)

            if not p:
                inform = 0
                if not find_local_package(server, package):
                    if allow_unsub:
                        rctalk.error("Unable to find package '" + package + "'")
                    else:
                        rctalk.error("Unable to find package '" + package + "' in any subscribed channel")
                    sys.exit(1)
                else:
                    p = package

            if inform:
                rctalk.message("Using " + p["name"] + " " +
                               rcformat.evr_to_str(p) + " from the '" +
                               rcchannelutils.channel_id_to_name(server, p["channel"]) +
                               "' channel")
                
            packages_to_install.append(p)

        if not packages_to_install:
            rctalk.message("--- No packages to install ---")
            sys.exit(0)

        try:
            dep_install, dep_remove = server.rcd.packsys.resolve_dependencies(packages_to_install, [])
        except ximian_xmlrpclib.Fault, f:
            if f.faultCode == -604:
                rctalk.error(f.faultString)
                sys.exit(1)
            else:
                raise

        if rctalk.show_verbose:
            rctalk.message("The following requested packages will be installed:")
            format_dependencies(server, packages_to_install)

        if dep_install:
            rctalk.message("The following additional packages will be installed:")
            format_dependencies(server, dep_install)

        if dep_remove:
            rctalk.message("The following packages must be REMOVED:")
            format_dependencies(server, dep_remove)

        if not options_dict.has_key("no-confirmation") and (dep_install or dep_remove):
            confirm = raw_input("Do you want to continue? [Y/n] ")
            if confirm and not (confirm[0] == "y" or confirm[0] == "Y"):
                rctalk.message("Aborted.")
                sys.exit(0)

        if options_dict.has_key("no-confirmation") and not options_dict.has_key("allow-removals"):
            rctalk.warning("Removals are required.  Use the -d option or confirm interactively.")
            sys.exit(1)

        transact_and_poll(server,
                          packages_to_install + extract_packages(dep_install),
                          extract_packages(dep_remove),
                          dry_run)


###
### "remove" command
###

class PackageRemoveCmd(rccommand.RCCommand):

    def name(self):
        return "remove"

    def arguments(self):
        return "<package-name> <package-name> ..."

    def description_short(self):
        return "Remove packages"

    def local_opt_table(self):
        return [["y", "no-confirmation", "", "Perform the actions without confirmation"]]

    def execute(self, server, options_dict, non_option_args):
        packages_to_remove = []
        
        if options_dict.has_key("dry-run"):
            dry_run = 1
        else:
            dry_run = 0

        for a in non_option_args:
            p = find_package_on_system(server, a)

            if not p:
                rctalk.error("Unable to find package '" + a + "'")
                sys.exit(1)
                
            packages_to_remove.append(p)

        if not packages_to_remove:
            rctalk.message("--- No packages to remove ---")
            sys.exit(0)

        try:
            dep_install, dep_remove = server.rcd.packsys.resolve_dependencies([], packages_to_remove)
        except ximian_xmlrpclib.Fault, f:
            if f.faultCode == -604:
                rctalk.error(f.faultString)
                sys.exit(1)
            else:
                raise

        if rctalk.show_verbose:
            rctalk.message("The following requested packages will be REMOVED:")
            format_dependencies(server, packages_to_remove)

        if dep_install:
            rctalk.message("The following additional packages will be installed:")
            format_dependencies(server, dep_install)

        if dep_remove:
            rctalk.message("The following packages must also be REMOVED:")
            format_dependencies(server, dep_remove)

        if not options_dict.has_key("no-confirmation") and (dep_install or dep_remove):
            confirm = raw_input("Do you want to continue? [Y/n] ")
            if confirm and not (confirm[0] == "y" or confirm[0] == "Y"):
                rctalk.message("Aborted.")
                sys.exit(0)

        transact_and_poll(server,
                          extract_packages(dep_install),
                          packages_to_remove + extract_packages(dep_remove),
                          dry_run)


###
### "update-all" command
###

class PackageUpdateAllCmd(rccommand.RCCommand):

    def name(self):
        return "update-all"

    def arguments(self):
        return "<channel> <channel> ..."

    def description_short(self):
        return "Download and install available updates"

    def local_opt_table(self):
        return [["d", "allow-removals", "", "Allow removals with no confirmation"],
                ["y", "no-confirmation", "", "Perform the actions without confirmation"]]

    def execute(self, server, options_dict, non_option_args):
        if options_dict.has_key("dry-run"):
            dry_run = 1
        else:
            dry_run = 0

        up = get_updates(server, non_option_args)

        # x[1] is the package to be updated
        packages_to_install = map(lambda x:x[1], up)

        if not packages_to_install:
            rctalk.message("--- No packages to update ---")
            sys.exit(0)

        try:
            dep_install, dep_remove = server.rcd.packsys.resolve_dependencies(packages_to_install, [])
        except ximian_xmlrpclib.Fault, f:
            if f.faultCode == -604:
                rctalk.error(f.faultString)
                sys.exit(1)
            else:
                raise

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

        transact_and_poll(server,
                          packages_to_install + extract_packages(dep_install),
                          extract_packages(dep_remove),
                          dry_run)


###
### "verify" command
###

class PackageVerifyCmd(rccommand.RCCommand):

    def name(self):
        return "verify"

    def arguments(self):
        return ""

    def description_short(self):
        return "Verify system dependencies"

    def local_opt_table(self):
        return [["d", "allow-removals", "", "Allow removals with no confirmation"],
                ["y", "no-confirmation", "", "Perform the actions without confirmation"]]

    def execute(self, server, options_dict, non_option_args):
        if options_dict.has_key("dry-run"):
            dry_run = 1
        else:
            dry_run = 0

        try:
            dep_install, dep_remove = server.rcd.packsys.verify_dependencies()
        except ximian_xmlrpclib.Fault, f:
            if f.faultCode == -604:
                rctalk.error(f.faultString)
                sys.exit(1)
            else:
                raise

        if dep_install:
            rctalk.message("The following packages must be installed:")
            format_dependencies(server, dep_install)

        if dep_remove:
            rctalk.message("The following packages must be REMOVED:")
            format_dependencies(server, dep_remove)

        if not options_dict.has_key("no-confirmation") and (dep_install or dep_remove):
            confirm = raw_input("Do you want to continue? [Y/n] ")
            if confirm and not (confirm[0] == "y" or confirm[0] == "Y"):
                rctalk.message("Aborted.")
                sys.exit(0)

        if options_dict.has_key("no-confirmation") and not options_dict.has_key("allow-removals"):
            rctalk.warning("Removals are required.  Use the -d option or confirm interactively.")
            sys.exit(1)

        transact_and_poll(server,
                          extract_packages(dep_install),
                          extract_packages(dep_remove),
                          dry_run)

###
### "solvedeps" command
###

class PackageSolveCmd(rccommand.RCCommand):

    def name(self):
        return "solvedeps"

    def aliases(self):
        return ["solve"]

    def arguments(self):
        return "<package-dep>"

    def execute(self, server, options_dict, non_option_args):
        if options_dict.has_key("dry-run"):
            dry_run = 1
        else:
            dry_run = 0

        dlist = []

        for d in non_option_args:
            dep = {}
            dep["name"] = d
            dep["relation"] = "(any)"
            dep["has_epoch"] = 0
            dep["epoch"] = 0
            dep["version"] = "foo"
            dep["release"] = "bar"

            dlist.append(dep)

        try:
            dep_install, dep_remove = server.rcd.packsys.solve_dependencies(dlist)
        except ximian_xmlrpclib.Fault, f:
            if f.faultCode == -604:
                rctalk.error(f.faultString)
                sys.exit(1)
            else:
                raise

        if not dep_install and not dep_remove:
            rctalk.message("Those dependencies are already satisfied on the system")
            sys.exit(0)

        if dep_install:
            rctalk.message("The following packages must be installed:")
            format_dependencies(server, dep_install)

        if dep_remove:
            rctalk.message("The following packages must be REMOVED:")
            format_dependencies(server, dep_remove)

        if not options_dict.has_key("no-confirmation") and (dep_install or dep_remove):
            confirm = raw_input("Do you want to continue? [Y/n] ")
            if confirm and not (confirm[0] == "y" or confirm[0] == "Y"):
                rctalk.message("Aborted.")
                sys.exit(0)

        if options_dict.has_key("no-confirmation") and not options_dict.has_key("allow-removals"):
            rctalk.warning("Removals are required.  Use the -d option or confirm interactively.")
            sys.exit(1)

        transact_and_poll(server,
                          extract_packages(dep_install),
                          extract_packages(dep_remove),
                          dry_run)

###
### "debug" command
###

class PackageDebugCmd(rccommand.RCCommand):

    def name(self):
        return "debug"

    def arguments(self):
        return "<file>"

    def description_short(self):
        return "Get a dump of the system for debugging"

    def execute(self, server, options_dict, non_option_args):
        if non_option_args:
            try:
                f = open(non_option_args[0], "w")
            except IOError, e:
                rctalk.error("Couldn't open '" + non_option_args[0] + "' for writing: " + e.strerror)
                sys.exit(1)
            my_open = 1
        else:
            f = sys.stdout
            my_open = 0

        rctalk.message("Getting a dump of the system.  Note: This could take several moments.")

        f.write(zlib.decompress(server.rcd.packsys.dump().data))
        f.flush()

        if my_open:
            f.close()

        rctalk.message("Dump finished.")
        
###
### Don't forget to register!
###

rccommand.register(PackagesCmd)
rccommand.register(PackageSearchCmd)
rccommand.register(PackageUpdatesCmd)
rccommand.register(SummaryCmd)
rccommand.register(PackageInfoCmd)
rccommand.register(PackageInstallCmd)
rccommand.register(PackageRemoveCmd)
rccommand.register(PackageUpdateAllCmd)
rccommand.register(PackageVerifyCmd)
rccommand.register(PackageDebugCmd)
rccommand.register(PackageSolveCmd)
