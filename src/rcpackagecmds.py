###
### Copyright 2002-2003 Ximian, Inc.
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the GNU General Public License, version 2,
### as published by the Free Software Foundation.
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

import string
import sys
import time
import zlib

import rcfault
import rcformat
import rccommand
import rcchannelutils
import rcpackageutils
import rctalk
import ximian_xmlrpclib

###
### "packages" command
###

class PackagesCmd(rccommand.RCCommand):

    def name(self):
        return "packages"

    def aliases(self):
        return ["pa"]

    def category(self):
        return "basic"

    def is_basic(self):
        return 1

    def arguments(self):
        return "<channel> <channel> ..."

    def description_short(self):
        return "List the packages in a channel"

    def category(self):
        return "package"

    def local_opt_table(self):
        return [["",  "no-abbrev", "", "Do not abbreviate channel or version information"],
                ["i", "installed-only", "", "Show only installed packages"],
                ["u", "uninstalled-only", "", "Show only uninstalled packages"],
                ["",  "sort-by-name", "", "Sort packages by name (default)"],
                ["",  "sort-by-channel", "", "Sort packages by channel"]]

    def local_orthogonal_opts(self):
        return [["installed-only", "uninstalled-only"]]

    def execute(self, server, options_dict, non_option_args):

        packages = []
        package_table = []

        multiple_channels = 1

        query = []
        clist = []
            
        for a in non_option_args:

                cl = rcchannelutils.get_channels_by_name(server, a)

                if rcchannelutils.validate_channel_list(a, cl):
                    clist = clist + cl

        if non_option_args and not clist:
            sys.exit(1)

        query = map(lambda c:["channel", "=", c["id"]], clist)

        if len(clist) > 1:
            query.insert(0, ["", "begin-or", ""])
            query.append(["", "end-or", ""])

        if options_dict.has_key("installed-only"):
            query.append(["name-installed", "=", "true"])
        elif options_dict.has_key("uninstalled-only"):
            query.append(["package-installed", "=", "false"])

        if len(clist) == 1:
            multiple_channels = 0

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

        # If we're getting all of the packages available to us, filter out
        # ones in the "hidden" channels, like the system packages channel.
        packages = rcpackageutils.filter_visible_channels(server, packages)
        
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

class PackageSearchCmd(rccommand.RCCommand):

    def name(self):
        return "search"

    def aliases(self):
        return ["se"]

    def is_basic(self):
        return 1

    def arguments(self):
        return "<search-string> <search-string>..."

    def description_short(self):
        return "Search for a package"
    
    def category(self):
        return "package"
        
    def local_opt_table(self):
        return [["", "match-all", "",              "Search for a match to all search strings (default)"],
                ["", "match-any", "",              "Search for a match to any of the search strings"],
                ["", "match-substrings", "",       "Matches for search strings may be partial words"],
                ["", "match-words",      "",       "Matches for search strings must be whole words"],
                ["d", "search-descriptions", "",   "Search in package descriptions, but not package names"],
                ["i", "installed-only",   "",      "Show only packages that are already installed"],
                ["u", "uninstalled-only", "",      "Show only packages that are not currently installed"],
                ["",  "locked-only", "",           "Show only locked packages"],
                ["",  "unlocked-only", "",         "Show only unlocked packages"],
                ["c", "channel",        "channel", "Show only the packages from the channel you specify"],
                ["", "sort-by-name",     "",       "Sort packages by name (default)"],
                ["", "sort-by-channel",  "",       "Sort packages by channel, not by name"],
                ["", "no-abbrev", "",              "Do not abbreviate channel or version information"]]

    def local_orthogonal_opts(self):
        return [["match-any", "match-all"],
                ["match-substrings", "match-words"],
                ["installed-only", "uninstalled-only"],
                ["sort-by-name", "sort-by-channel"],
                ["locked-only", "unlocked-only"]]

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
            query.append(["package-installed", "=", "true"])
        elif options_dict.has_key("uninstalled-only"):
            query.append(["package-installed", "=", "false"])

        if options_dict.has_key("channel"):
            cname = options_dict["channel"]
            clist = rcchannelutils.get_channels_by_name(server,cname)
            if not rcchannelutils.validate_channel_list(cname, clist):
                sys.exit(1)
            c = clist[0]

            query.append(["channel", "=", c["id"]])

        packages = server.rcd.packsys.search(query)

        if options_dict.has_key("locked-only") or options_dict.has_key("unlocked-only"):
            if options_dict.has_key("locked-only"):
                packages = filter(lambda p:p["locked"], packages)
            elif options_dict.has_key("unlocked-only"):
                packages = filter(lambda p:not p["locked"], packages)

        # Filter out packages which are in "hidden" channels, like the
        # system packages channel.
        packages = rcpackageutils.filter_visible_channels(server, packages)

        package_table = []
        no_abbrev = options_dict.has_key("no-abbrev")

        for p in packages:
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
### "list-updates" command
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
        last_desc = None
        for d in descriptions:
            if last_desc != d: # don't print the same damn message many times
                rctalk.message(header + d)
            last_desc = d
            header = "              "

        rctalk.message("")
        

class PackageListUpdatesCmd(rccommand.RCCommand):

    def name(self):
        return "list-updates"

    def is_basic(self):
        return 1

    def aliases(self):
        return ["lu"]

    def arguments(self):
        return "<channel> <channel> ..."

    def description_short(self):
        return "List available updates"

    def category(self):
        return "package"

    def local_opt_table(self):
        return [["",  "sort-by-name", "", "Sort updates by name"],
                ["",  "sort-by-channel", "", "Sort updates by channel"],
                ["",  "no-abbrev", "", "Do not abbreviate channel or version information"],
                ["i", "importance", "importance", "Show only updates as or more important than 'importance' (valid are " + rcformat.importance_str_summary() + ")"]]

    def execute(self, server, options_dict, non_option_args):

        no_abbrev = options_dict.has_key("no-abbrev") or \
                    options_dict.has_key("terse")

        min_importance = None
        if options_dict.has_key("importance"):
            if not rcpackageutils.update_importances.has_key(options_dict["importance"]):
                rctalk.warning("Invalid importance: " +
                               options_dict["importance"])
            else:
                min_importance = rcpackageutils.update_importances[options_dict["importance"]]

        update_list = rcpackageutils.get_updates(server, non_option_args)

        if min_importance != None:
            up = []
            for u in update_list:
                # higher priorities have lower numbers... i know, i know...
                if u[1]["importance_num"] <= min_importance:
                    up.append(u)
        else:
            up = update_list
        
        if not up:
            if non_option_args:
                rctalk.message("No updates are available in the specified channels.")
            else:
                rctalk.message("No updates are available.")

                if not filter(lambda x:x["subscribed"], rcchannelutils.get_channels(server)):
                    rctalk.message("")
                    rctalk.warning("Updates are only visible when you are subscribed to a channel.")
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

    def is_basic(self):
        return 1

    def aliases(self):
        return ["su", "sum"]

    def arguments(self):
        return ""

    def description_short(self):
        return "Display a summary of available updates"

    def category(self):
        return "package"

    def local_opt_table(self):
        return [["", "no-abbrev", "", "Do not abbreviate channel names or importance levels"]]

    def execute(self, server, options_dict, non_option_args):

        no_abbrev = options_dict.has_key("no-abbrev")

        update_list = rcpackageutils.get_updates(server, [])

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

    def is_basic(self):
        return 1

    def aliases(self):
        return ["if"]

    def category(self):
        return "package"

    def arguments(self):
        return "<package-name>"

    def description_short(self):
        return "Show detailed information about a package"

    def local_opt_table(self):
        return [["u", "allow-unsubscribed", "", "Search in unsubscribed channels as well"]]

    def execute(self, server, options_dict, non_option_args):

        if not non_option_args:
            self.usage()
            sys.exit(1)

        if options_dict.has_key("allow-unsubscribed"):
            allow_unsub = 1
        else:
            allow_unsub = 0

        plist = []

        for a in non_option_args:
            inform = 0
            channel = None
            package = None

            plist = plist + rcpackageutils.find_package(server, a, allow_unsub)

        if not plist:
            rctalk.message("--- No packages found ---")
            sys.exit(1)

        for p in plist:
            pinfo = server.rcd.packsys.package_info(p)

            rctalk.message("")
            rctalk.message("Name: " + p["name"])
            rctalk.message("Version: " + p["version"])
            rctalk.message("Release: " + p["release"])
            if pinfo.get("file_size", 0):
                rctalk.message("Package size: " + str(pinfo["file_size"]))
            if pinfo.get("installed_size", 0):
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


###
### "info-provides" command
###

### FIXME: this is pretty minimalistic

class PackageInfoProvidesCmd(rccommand.RCCommand):

    def name(self):
        return "info-provides"

    def aliases(self):
        return ["ip"]

    def arguments(self):
        return "<package> ..."

    def category(self):
        return "dependency"

    def description_short(self):
        return "List a package's provides"

    def execute(self, server, options_dict, non_option_args):

        if len(non_option_args) < 1:
            self.usage()
            sys.exit(1)

        plist = []

        for a in non_option_args:
            plist = plist + rcpackageutils.find_package(server, a, 1)

        if not plist:
            rctalk.message("--- No packages found ---")
            sys.exit(1)

        for pkg in plist:
            dep_info = server.rcd.packsys.package_dependency_info(pkg)

            if not dep_info.has_key("provides"):
                continue

            rctalk.message("--- %s %s ---" %
                           (pkg["name"], rcformat.evr_to_str(pkg)))

            for dep in dep_info["provides"]:
                rctalk.message(rcformat.dep_to_str(dep))

            rctalk.message("")
            

###
### "info-requirements" command
###

class PackageInfoRequirementsCmd(rccommand.RCCommand):

    def name(self):
        return "info-requirements"

    def aliases(self):
        return ["ir"]

    def arguments(self):
        return "<package> ..."

    def description_short(self):
        return "List a package's requirements"

    def category(self):
        return "dependency"

    def local_opt_table(self):
        return [["i", "installed-providers", "", "If a required package is already installed, do not list alternatives (default)"],
                ["a", "all-providers", "", "List all packages that can satisfy a requirement"],
                ["v", "show-versions", "", "Display full version information for packages"],
                ["",  "no-abbrev", "", "Do not abbeviate channel or version information"]]

    def local_orthogonal_opts(self):
        return [["installed-providers", "all-providers"]]

    def execute(self, server, options_dict, non_option_args):

        if len(non_option_args) < 1:
            self.usage()
            sys.exit(1)

        no_abbrev = options_dict.has_key("no-abbrev")

        plist = []

        for a in non_option_args:
            plist = plist + rcpackageutils.find_package(server, a, 1)

        if not plist:
            rctalk.message("--- No packages found ---")
            sys.exit(1)

        for pkg in plist:
            dep_info = server.rcd.packsys.package_dependency_info(pkg)

            if not dep_info.has_key("requires"):
                continue

            table = []

            row_spec = ["name", "channel"]
            row_headers = ["Provided By", "Channel"]
            pad = []

            if options_dict.has_key("show-versions"):
                row_spec.insert(1, "version")
                row_headers.insert(1, "Version")
                pad = pad + [""]

            if options_dict.has_key("all-providers"):
                row_spec.insert(2, "installed")
                row_headers.insert(2, "S")
                pad = pad + [""]

            for dep in dep_info["requires"]:
                providers = map(lambda x:x[0], server.rcd.packsys.what_provides(dep))
                prov_dict = {}

                name = rcformat.dep_to_str(dep)
                status = "*"
                for prov in providers:
                    if prov["installed"]:
                        status = ""

                if status == "" \
                       and not options_dict.has_key("all-providers"):
                    providers = filter(lambda x:x["installed"], providers)


                count = 0
                for prov in providers:
                    row = rcformat.package_to_row(server, prov, no_abbrev, row_spec)
                    key = string.join(row)
                    if not prov_dict.has_key(key):
                        table.append([status, name] + row)
                        prov_dict[key] = 1
                        status = ""
                        name = ""
                        count = count + 1

                if count == 0:
                    table.append(["*", name, "(none)", "(none)"] + pad)
                elif count > 1 and not rctalk.be_terse:
                    table.append(["", "", "", ""] + pad)

            if len(plist) > 1:
                rctalk.message("--- %s %s ---" %
                               (pkg["name"], rcformat.evr_to_str(pkg)))

            if not table:
                rctalk.message("--- No requirements ---")
            else:
                rcformat.tabular(["!", "Requirement"] + row_headers, table)

            if len(plist) > 1:
                rctalk.message("")


###
### "info-children" command
###

class PackageInfoChildrenCmd(rccommand.RCCommand):

    def name(self):
        return "info-children"

    def aliases(self):
        return ["ichild"]

    def arguments(self):
        return "<package> ..."

    def description_short(self):
        return "List a package set's children"

    def category(self):
        return "dependency"

    def local_opt_table(self):
        return [["i", "installed-providers", "", "If a required package is already installed, do not list alternatives (default)"],
                ["a", "all-providers", "", "List all packages that can satisfy a requirement"],
                ["v", "show-versions", "", "Display full version information for packages"],
                ["",  "no-abbrev", "", "Do not abbeviate channel or version information"]]

    def local_orthogonal_opts(self):
        return [["installed-providers", "all-providers"]]

    def execute(self, server, options_dict, non_option_args):

        if len(non_option_args) < 1:
            self.usage()
            sys.exit(1)

        no_abbrev = options_dict.has_key("no-abbrev")

        plist = []

        for a in non_option_args:
            plist = plist + rcpackageutils.find_package(server, a, 1)

        if not plist:
            rctalk.message("--- No packages found ---")
            sys.exit(1)

        for pkg in plist:
            dep_info = server.rcd.packsys.package_dependency_info(pkg)

            if not dep_info.has_key("children"):
                continue

            table = []

            row_spec = ["name", "channel"]
            row_headers = ["Provided By", "Channel"]
            pad = []

            if options_dict.has_key("show-versions"):
                row_spec.insert(1, "version")
                row_headers.insert(1, "Version")
                pad = pad + [""]

            if options_dict.has_key("all-providers"):
                row_spec.insert(2, "installed")
                row_headers.insert(2, "S")
                pad = pad + [""]

            for dep in dep_info["children"]:
                providers = map(lambda x:x[0], server.rcd.packsys.what_provides(dep))
                prov_dict = {}

                name = rcformat.dep_to_str(dep)
                status = "*"
                for prov in providers:
                    if prov["installed"]:
                        status = ""

                if status == "" \
                       and not options_dict.has_key("all-providers"):
                    providers = filter(lambda x:x["installed"], providers)


                count = 0
                for prov in providers:
                    row = rcformat.package_to_row(server, prov, no_abbrev, row_spec)
                    key = string.join(row)
                    if not prov_dict.has_key(key):
                        table.append([status, name] + row)
                        prov_dict[key] = 1
                        status = ""
                        name = ""
                        count = count + 1

                if count == 0:
                    table.append(["*", name, "(none)", "(none)"] + pad)
                elif count > 1 and not rctalk.be_terse:
                    table.append(["", "", "", ""] + pad)

            if len(plist) > 1:
                rctalk.message("--- %s %s ---" %
                               (pkg["name"], rcformat.evr_to_str(pkg)))

            if not table:
                rctalk.message("--- No Children ---")
            else:
                rcformat.tabular(["!", "Requirement"] + row_headers, table)

            if len(plist) > 1:
                rctalk.message("")

        
###
### "info-conflicts" command
###

def evr_eq(a, b):
    for x in ["name", "version", "release", "epoch"]:
        if a.has_key(x) != b.has_key(x) or \
           (a.has_key(x) and a[x] != b[x]):
            return 0
    return 1
        

class PackageInfoConflictsCmd(rccommand.RCCommand):
    
    def name(self):
        return "info-conflicts"

    def aliases(self):
        return ["ic"]

    def arguments(self):
        return "<package>"

    def description_short(self):
        return "List all conflicts for the package"

    def category(self):
        return "dependency"

    def execute(self, server, options_dict, non_option_args):

        if len(non_option_args) < 1:
            self.usage()
            sys.exit(1)

        plist = []

        for a in non_option_args:
            plist = plist + rcpackageutils.find_package(server, a, 1)

        if not plist:
            rctalk.message("--- No packages found ---")
            sys.exit(1)

        for pkg in plist:
            dep_info = server.rcd.packsys.package_dependency_info(pkg)

            if not dep_info.has_key("conflicts"):
                continue

            table = []

            for dep in dep_info["conflicts"]:
                provided_by = map(lambda x:x[0], server.rcd.packsys.what_provides(dep))
                conf_dict = {}

                name = rcformat.dep_to_str(dep)
                count = 0
                for provider in provided_by:
                    # skip self-conflicts
                    if evr_eq(provider, pkg):
                        continue

                    if provider["installed"]:
                        status = "*"
                    else:
                        status = ""

                    row = rcformat.package_to_row(server, provider, 0, ["name", "installed", "channel"])
                    key = string.join(row)
                    if not conf_dict.has_key(key):
                        table.append([status, name] + row)
                        conf_dict[key] = 1
                        status = ""
                        name = ""
                        count = count + 1

                if count == 0:
                    table.append(["", name, "", "", ""])
                elif count > 1:
                    table.append(["", "", "", "", ""])

            if len(plist) > 1:
                rctalk.message("--- %s %s ---" %
                               (pkg["name"], rcformat.evr_to_str(pkg)))

            if not table:
                rctalk.message("--- No conflicts ---")
            else:
                rcformat.tabular(["!", "Conflict", "Provided By", "S", "Channel"], table)

            if len(plist) > 1:
                rctalk.message("")
                

###
### "info-obsoletes" command
###

class PackageInfoObsoletesCmd(rccommand.RCCommand):
    
    def name(self):
        return "info-obsoletes"

    def aliases(self):
        return ["io"]

    def arguments(self):
        return "<package>"

    def description_short(self):
        return "List all obsoletes for the package"

    def category(self):
        return "dependency"

    def execute(self, server, options_dict, non_option_args):

        if len(non_option_args) < 1:
            self.usage()
            sys.exit(1)

        plist = []

        for a in non_option_args:
            plist = plist + rcpackageutils.find_package(server, a, 1)

        if not plist:
            rctalk.message("--- No packages found ---")
            sys.exit(1)

        for pkg in plist:
            dep_info = server.rcd.packsys.package_dependency_info(pkg)

            if not dep_info.has_key("obsoletes"):
                continue

            table = []

            for dep in dep_info["obsoletes"]:
                provided_by = map(lambda x:x[0], server.rcd.packsys.what_provides(dep))
                ob_dict = {}

                name = rcformat.dep_to_str(dep)
                status = ""
                for provider in provided_by:
                    if provider["installed"]:
                        status = "*"

                count = 0
                for provider in provided_by:
                    # skip self-obsoletes
                    if evr_eq(provider, pkg):
                        continue

                    if provider["installed"]:
                        status = "*"
                    else:
                        status = ""
                    
                    row = rcformat.package_to_row(server, provider, 0, ["name", "installed", "channel"])
                    key = string.join(row)
                    if not ob_dict.has_key(key):
                        table.append([status, name] + row)
                        ob_dict[key] = 1
                        status = ""
                        name = ""
                        count = count + 1

                if count == 0:
                    table.append(["", name, "", "", ""])
                elif count > 1:
                    table.append(["", "", "", "", ""])

            if len(plist) > 1:
                rctalk.message("--- %s %s ---" %
                               (pkg["name"], rcformat.evr_to_str(pkg)))

            if not table:
                rctalk.message("--- No obsoletes ---")
            else:
                rcformat.tabular(["!", "Obsoletes", "Provided by", "S", "Channel"], table)

            if len(plist) > 1:
                rctalk.message("")
                

###
### "dump" command
###

class PackageDumpCmd(rccommand.RCCommand):

    def name(self):
        return "dump"

    def arguments(self):
        return "<file>"

    def description_short(self):
        return "Get an XML dump of system information"

    def category(self):
        return "system"

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

        sys.stderr.write("Getting a dump of the system.  Note: This could take several moments.\n")
        
        f.write(zlib.decompress(server.rcd.packsys.dump().data))
        f.flush()

        if my_open:
            f.close()

        sys.stderr.write("Dump finished.\n")

###
### "dangling requires" command
###

class PackageDanglingRequiresCmd(rccommand.RCCommand):

    def name(self):
        return "dangling-requires"

    def aliases(self):
        return ["dr"]

    def description_short(self):
        return "Search for packages with requirements that are not provided " \
               "by any other package."

    def category(self):
        return "dependency"

    def execute(self, server, options_dict, non_option_args):
        danglers = server.rcd.packsys.find_dangling_requires()
        if not danglers:
            rctalk.message("No dangling requires found.")
            sys.exit(0)

        table = []

        for d in danglers:
            pkg = d[0]["name"]
            cid = d[0].get("channel", d[0].get("channel_guess", 0))
            channel = rcchannelutils.channel_id_to_name(server, cid)
            if not channel:
                channel = "(none)"
            for r in d[1:]:
                table.append([pkg, channel, rcformat.dep_to_str(r)])
                pkg = ""
                channel = ""

        rcformat.tabular(["Package", "Channel", "Requirement"], table)

###
### "file list" command
###

class PackageFileListCmd(rccommand.RCCommand):

    def name(self):
        return "file-list"

    def is_basic(self):
        return 1

    def aliases(self):
        return ["fl"]

    def category(self):
        return "package"

    def arguments(self):
        return "<package or file>"

    def description_short(self):
        return "List files within a package"

    def execute(self, server, options_dict, non_option_args):
        if len(non_option_args) != 1:
            self.usage()
            sys.exit(1)

        plist = rcpackageutils.find_package(server, non_option_args[0], 1)

        if not plist:
            rctalk.message("--- No package found ---")
            sys.exit(1)

        pkg = None
        for p in plist:
            if p["installed"] or p.get("package_filename", None):
                pkg = p
                break

        if not pkg:
            rctalk.message("--- File information not available ---")
            sys.exit(1)

        try:
            file_list = server.rcd.packsys.file_list(pkg)
        except ximian_xmlrpclib.Fault, f:
            if f.faultCode == rcfault.undefined_method:
                rctalk.error("File list is not supported by this daemon")
                sys.exit(1)
            else:
                raise

        if not file_list:
            rctalk.message("--- No files available ---")

        for f in file_list:
            print f

class PackageForFileCmd(rccommand.RCCommand):

    def name(self):
        return "package-file"

    def is_basic(self):
        return 1

    def aliases(self):
        return ["pf"]

    def category(self):
        return "package"

    def arguments(self):
        return "<file>"

    def description_short(self):
        return "Get package which contains file"

    def local_opt_table(self):
        return [["",  "no-abbrev", "", "Do not abbreviate channel or version information"]]

    def execute(self, server, options_dict, non_option_args):
        if len(non_option_args) != 1:
            self.usage()
            sys.exit(1)

        filename = non_option_args[0]

        try:
            plist = server.rcd.packsys.find_package_for_file(filename)
        except ximian_xmlrpclib.Fault, f:
            if f.faultCode == rcfault.package_not_found:
                rctalk.error("No package owns file '%s'" % filename)
                sys.exit(1)
            else:
                raise

        for p in plist:
            if options_dict.has_key("no-abbrev"):
                rctalk.message("%s %s" % (p["name"],
                                          rcformat.evr_to_str(p)))
            else:
                rctalk.message("%s %s" % (p["name"],
                                          rcformat.evr_to_abbrev_str(p)))
        
###
### Don't forget to register!
###

rccommand.register(PackagesCmd)
rccommand.register(PackageSearchCmd)
rccommand.register(PackageListUpdatesCmd)
rccommand.register(SummaryCmd)
rccommand.register(PackageInfoCmd)
rccommand.register(PackageInfoProvidesCmd)
rccommand.register(PackageInfoRequirementsCmd)
rccommand.register(PackageInfoChildrenCmd)
rccommand.register(PackageInfoConflictsCmd)
rccommand.register(PackageInfoObsoletesCmd)
rccommand.register(PackageDumpCmd)
rccommand.register(PackageDanglingRequiresCmd)
rccommand.register(PackageFileListCmd)
rccommand.register(PackageForFileCmd)
