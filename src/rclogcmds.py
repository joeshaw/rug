###
### Copyright 2002 Ximian, Inc.
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

import sys
import string
import time
import rctalk
import rcformat
import rccommand

def format_user_str(item):

    user = item["user"]
    host = item["host"]

    if host == "local" or host == "localhost":
        return user
    else:
        return user + "@" + host

###
### This is our default output format.  It should pretty much always
### fit nicely in 80 columns.
###

def log_entries_to_quick_table(entries):

    log_table = []

    for item in entries:

        date_str = time.strftime("%Y-%m-%d", time.localtime(item["timestamp"]))

        if item.has_key("pkg_final"):
            pkg = item["pkg_final"]
        else:
            pkg = item["pkg_initial"]
        
        log_table.append([date_str, item["action"], pkg["name"],
                          rcformat.evr_to_abbrev_str(pkg)])

    if log_table:
        rcformat.tabular(["Date", "Action", "Package", "Version"], log_table)
    else:
        rctalk.message("No matches.")


###
### This is the minimalistic output format we use when --terse is in effect.
### 

def log_entries_to_table(entries):

    log_table = []

    for x in entries:

        pkg_initial = "-"
        if x.has_key("pkg_initial"):
            pkg_initial = rcformat.evr_to_str(x["pkg_initial"])

        pkg_final = "-"
        if x.has_key("pkg_final"):
            pkg_final = rcformat.evr_to_str(x["pkg_final"])
                
        log_table.append([x["time_str"],
                          x["action"],
                          x["host"],
                          x["user"],
                          pkg_initial,
                          pkg_final])

    if log_table:
        rcformat.tabular(["Time", "Action", "Host", "User", "Initial", "Final"], log_table)
    else:
        rctalk.message("No matches.")


###
### Here we don't even try to construct a table.  This lets us show lots of
### information w/o worrying about being too wide for the screen.
### We use this format when the --verbose option has been passed.
###

def log_entries_list(entries):

    for item in entries:

        user_str = format_user_str(item)

        rctalk.message("   Time: " + item["time_str"])
        rctalk.message("   User: " + user_str)
        rctalk.message(" Action: " + item["action"])

        if item.has_key("pkg_initial") and item.has_key("pkg_final"):
            init = item["pkg_initial"]
            rctalk.message(" Before: " + init["name"] + \
                           rcformat.evr_to_str(init))

            fin = item["pkg_final"]
            rctalk.message("  After: " + fin["name"] + \
                           rcformat.evr_to_str(fin))

        else:

            if item.has_key("pkg_initial"):
                pkg = item["pkg_initial"]
            else:
                pkg = item["pkg_final"]

            if pkg:
                rctalk.message("Package: " + pkg["name"] + " " + \
                               rcformat.evr_to_str(pkg))


        rctalk.message("")


class LogQueryCmd(rccommand.RCCommand):

    def name(self):
        return "history"

    def aliases(self):
        return ["hi"]

    def arguments(self):
        return "<search-string> <search-string> ..."

    def description_short(self):
        return "Search log entries"

    def local_opt_table(self):
        return [["n", "search-name",   "", "Search by package name (default)"],
                ["a", "search-action", "", "Search by action"],
                ["",  "search-host",   "", "Search by host"],
                ["",  "search-user",   "", "Search by user"],
                ["",  "match-all",     "", "Require packages to match all search strings (default)"],
                ["",  "match-any",     "", "Allow packages to match any search string"],
                ["",  "match-substrings", "", "Match search strings against any part of the text"],
                ["",  "match-words",   "", "Require search strings to match entire words"],
                ["d", "days-back",     "num of days", "Maximum number of days to look back (default 30)."]]

    def execute(self, server, options_dict, non_option_args):

        ## First we assemble our query.

        key = "name"
        if options_dict.has_key("search-action"):
            key = "action"
        elif options_dict.has_key("search-host"):
            key = "host"
        elif options_dict.has_key("search-user"):
            key = "user"

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

        days_back = 30
        if options_dict.has_key("days-back"):
            db = options_dict["days-back"]
            try:
                db = float(db)
            except:
                db = -1

            if db <= 0:
                rctalk.warning("Ignoring invalid argument to --days-back option.")
            else:
                days_back = db

        secs_back = int(days_back * 86400)  # 1 day = 86400 sec

        query.append(["cutoff_time", "<=", str(secs_back)])

        ## Pass our query to the server, and get a pile of log entries back.
        ## We need to sort them, since they aren't guaranteed to be in any
        ## particular order.

        entries = server.rcd.log.query_log(query)
        entries.sort(lambda x,y:cmp(x["timestamp"], y["timestamp"]))

        ## The way we display the data depends on how
        ## talkative we have been told to be.

        if rctalk.be_terse:
            log_entries_to_table(entries)
        elif rctalk.show_verbose:
            log_entries_list(entries)
        else:
            log_entries_to_quick_table(entries)


rccommand.register(LogQueryCmd)
                
