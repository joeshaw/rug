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

class LogQueryCmd(rccommand.RCCommand):

    def name(self):
        return "log"

    def local_opt_table(self):
        return [["n", "search-name",   "", "Search by package name (default)"],
                ["a", "search-action", "", "Search by action"],
                ["",  "search-host",   "", "Search by host"],
                ["",  "search-user",   "", "Search by user"],
                ["d", "days-back",     "num of days", "Maximum number of days to look back (default 30)."]]

    def execute(self, server, options_dict, non_option_args):

        log_table = []

        search_type = "name"
        if options_dict.has_key("search-action"):
            search_type = "action"
        elif options_dict.has_key("search-host"):
            search_type = "host"
        elif options_dict.has_key("search-user"):
            search_type = "user"

        if not non_option_args:
            entries = server.rcd.log.query_log([])
        else:
            entries = server.rcd.log.query_log([(search_type, "contains", non_option_args[0])])

        entries.sort(lambda x,y:cmp(x["timestamp"], y["timestamp"]))

        for x in entries:
            log_table.append([x["time_str"],
                              x["action"],
                              x["host"],
                              x["user"],
                              "FOO",
                              "BAR"])

        if log_table:
            rcformat.tabular(["Time", "Action", "Host", "User", "Foo", "Bar"], log_table)
        else:
            rctalk.message("No matches.")


rccommand.register(LogQueryCmd, "Search Log Entries")
                
