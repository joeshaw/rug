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

import os
import sys
import string
import re
import rcutil
import rctalk
import rcformat
import rcchannelutils
import rccommand

def display_match(server, match, extra_head=[], extra_tail=[]):
    table = []

    if match.has_key("glob"):
        table.append(("Name Pattern:", match["glob"]))

    if match.has_key("dep"): # looks like a RCPackageDep
        dep = match["dep"]
        table.append(("Name:", dep["name"]))
        vers  = rcformat.rel_str(dep) + rcformat.evr_to_str(dep)
        table.append(("Version:", vers))

    if match.has_key("channel"):
        str = rcchannelutils.channel_id_to_name(server, match["channel"])
        table.append(("Channel:", str))

    if match.has_key("importance_num"):
        str = rcformat.importance_num_to_str(match["importance_num"])
        op = (match["importance_gteq"] and "<=") or ">="
        table.append(("Importance:", "%s %s" % (op, str)))

    table = extra_head + table + extra_tail

    maxlen = apply(max, map(lambda x:len(x[0]), table) + [0,])

    for label, val in table:
        rctalk.message("%s%s %s" % (" " * (maxlen - len(label)),
                                    label, val))

def lock_to_table_row(server, lock, no_abbrev):
    name = "(any)"
    channel = "(any)"
    importance = "(any)"

    # A match should have a glob or a dep, never both.
    if lock.has_key("glob"):
        name = lock["glob"]
    if lock.has_key("dep"):
        name = rcformat.dep_to_str(lock["dep"])
            
    if lock.has_key("channel"):
        channel = rcchannelutils.channel_id_to_name(server,
                                                        lock["channel"])
        if not no_abbrev:
            channel = rcformat.abbrev_channel_name(channel)

    if lock.has_key("importance_num"):
        imp = rcformat.importance_num_to_str(lock["importance_num"])
        op = (lock["importance_gteq"] and "<=") or ">="
        importance = op + " " + imp

    return [name, channel, importance]


def locks_to_table(server, locks, no_abbrev):
    table = []
    for l in locks:
        row = lock_to_table_row(server, l, no_abbrev)
        table.append(row)
    return table

def filter_package_dups(pkgs):

    def pkg_to_key(p):
        ch = p["channel"] or p.get("channel_guess", 0);
        return "%d:%s:%d:%s:%s" % \
               (ch, p["name"], p["epoch"], p["version"], p["release"])

    in_channel = {}
    for p in pkgs:
        if p["installed"] and p["channel"]:
            in_channel[pkg_to_key(p)] = 1

    filtered = []
    for p in pkgs:
        if p["channel"] != 0 or not in_channel.has_key(pkg_to_key(p)):
            filtered.append(p)

    return filtered


class LockListCmd(rccommand.RCCommand):

    def name(self):
        return "lock-list"

    def aliases(self):
        return ["ll"]

    def description_short(self):
        return "List package lock rules"

    def category(self):
        return "lock"

    def local_opt_table(self):
        return [["", "no-abbrev", "", "Do not abbreviate channel information"],
                ["m","matches", "", "Show information about matching packages"]]

    def execute(self, server, options_dict, non_option_args):
        locks = server.rcd.packsys.get_locks()

        verbose = options_dict.has_key("verbose")
        no_abbrev = options_dict.has_key("no-abbrev")
        matches = options_dict.has_key("matches")

        if locks:
            table = []
            count = 1
            for l in locks:
                pkgs = []
                if matches:
                    pkgs = server.rcd.packsys.search_by_package_match(l)
                    pkgs = filter_package_dups(pkgs)

                if verbose:
                    extra_head = [("Lock #:", str(count))]
                    extra_tail = []
                    if matches:
                        first = 1
                        for p in pkgs:
                            label = (first == 1 and "Matches:") or ""
                            first = 0
                            id = p.get("channel_guess", 0) or p["channel"]
                            if id:
                                channel = rcchannelutils.channel_id_to_name(server, id)
                                channel = "(%s)" % channel
                            else:
                                channel = ""
                            pkg_str = "%s %s %s" % (p["name"],
                                                    rcformat.evr_to_str(p),
                                                    channel)

                            extra_tail.append((label, pkg_str))
                    
                    display_match(server, l, extra_head, extra_tail)
                    rctalk.message("")
                            
                else:
                    row = lock_to_table_row(server, l, no_abbrev)
                    row.insert(0, str(count))
                    if matches:
                        row.append(str(len(pkgs)))
                    table.append(row)

                count = count + 1

            if not verbose:
                headers = ["#", "Pattern", "Channel", "Importance"]
                if matches:
                    headers.append("Matches")
                rcformat.tabular(headers, table)

        else:
            rctalk.message("--- No Locks Defined ---")



class LockAddCmd(rccommand.RCCommand):

    def name(self):
        return "lock-add"

    def aliases(self):
        return ["la"]

    def arguments(self):
        return "<name or pattern> [<relation> <version>]"

    def description_short(self):
        return "Add a package lock rule"

    def category(self):
        return "lock"

    def local_opt_table(self):
        return [["c", "channel", "channel",
                 "Channel to match in lock"],
                ["i", "importance", "importance",
                 "Lock against updates that are less important than "
                 "'importance' (valid are %s)" % rcformat.importance_str_summary()],
                ]

    def execute(self, server, options_dict, non_option_args):

        if len(non_option_args) < 1:
            self.usage()
            sys.exit(1)

        match = {}

        # Split non-option args on whitespace, reassembling the
        # pieces into a new list.
        non_option_args = reduce(lambda x,y: x+y,
                                 map(string.split, non_option_args))

        if len(non_option_args) == 3:
            name, relation, version = non_option_args

            if "?" in name or "*" in name:
                rctalk.warning("Wildcards are not allowed when specifying versioned locks.")
                sys.exit(1)

            valid_relations = ("=", "<", ">", "<=", ">=")
            if relation not in valid_relations:
                valid_str = string.join(map(lambda x: "'%s'" % x, valid_relations), ", ")
                rctalk.warning("'%s' is not a valid relation." % relation)
                rctalk.warning("Valid relations are: %s" % valid_str)
                sys.exit(1)

            match["dep"] = {"name": name,
                            "relation":relation,
                            "version_str":version }
            
        elif len(non_option_args) == 1:
            glob = non_option_args[0]
            # FIXME: It would be nice to verify that the incoming glob
            # is valid.  (It probably shouldn't contain whitespace, shouldn't
            # be the empty string, etc.)
            match["glob"] = glob
        elif len(non_option_args) != 0:
            rctalk.error("Unrecognized input \"%s\"" %
                         string.join(non_option_args, " "))
            sys.exit(1)
            
        if options_dict.has_key("channel"):
            cname = options_dict["channel"]
            clist = rcchannelutils.get_channels_by_name(server, cname)
            if not rcchannelutils.validate_channel_list(cname, clist):
                sys.exit(1)
            match["channel"] = clist[0]["id"]

        if options_dict.has_key("name"):
            # FIXME: It would be nice to verify that the incoming glob
            # is valid.  (It probably shouldn't contain whitespace, shouldn't
            # be the empty string, etc.)
            match["glob"] = options_dict["name"]

        if options_dict.has_key("importance"):
            num = rcformat.importance_str_to_num(options_dict["importance"])
            if num < 0:
                rctalk.error("'%s' is not a valid importance level" %
                             options_dict["importance"])
                sys.exit(1)

            # We want to match (i.e. lock) all packages below the given
            # importance.  Remember, in a match the opposite of >= is
            # <=, not <.  (Maybe this is broken, but it seems pretty
            # unnecessary to offer the full selection of comparison
            # operators.)
            match["importance_num"] = num
            match["importance_gteq"] = 0

        # FIXME: validate that the match isn't empty, etc.
        server.rcd.packsys.add_lock(match)

        rctalk.message("--- Added Lock ---")
        display_match(server, match)


class LockDeleteCmd(rccommand.RCCommand):

    def name(self):
        return "lock-delete"

    def aliases(self):
        return ["ld"]

    def arguments(self):
        return "<lock #>"

    def description_short(self):
        return "Remove a package log rule"

    def category(self):
        return "lock"

    def local_opt_table(self):
        return [["", "no-confirmation", "", "Permit removals without confirmation"]]

    def execute(self, server, options_dict, non_option_args):

        locks = server.rcd.packsys.get_locks()
        
        to_delete = []
        indices = []
        for x in non_option_args:
            success = 1
            try:
                i = int(x)
            except:
                success = 0

            if success:
                if 0 <= i-1 < len(locks):
                    indices.append(i)
                    to_delete.append(locks[i-1])
                else:
                    success = 0

            if not success:
                rctalk.warning("Ignoring invalid lock number '%s'" % x)

        if not to_delete:
            rctalk.warning("No valid lock numbers specified.")
            sys.exit(1)

        table = locks_to_table(server, to_delete, 1)
        for row, i in map(lambda x, y:(x, y), table, indices):
            row.insert(0, str(i))

        rcformat.tabular(["#", "Pattern", "Channel", "Importance"], table)

        if not options_dict.has_key("no-confirmation"):
            rctalk.message("")
            if len(to_delete) == 1:
                msg = "this lock"
            else:
                msg = "these locks"
            confirm = rctalk.prompt("Delete %s? [y/N]" % msg)
            if not confirm or not string.lower(confirm[0]) == "y":
                rctalk.message("Cancelled.")
                sys.exit(0)

        failures = []
        for l, i in map(lambda x, y: (x, y), to_delete, indices):
            retval = server.rcd.packsys.remove_lock(l)
            if not retval:
                failures.append(i)

        if failures:
            rctalk.warning("Unable to remove lock%s %s",
                           (len(failures) > 1 and "s") or "",
                           string.join(map(str, failures), ", "))
            sys.exit(1)

        
        
        

rccommand.register(LockListCmd)
rccommand.register(LockAddCmd)
rccommand.register(LockDeleteCmd)
