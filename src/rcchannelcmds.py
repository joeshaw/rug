###
### Copyright 2002 Ximian, Inc.
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the GNU General Public License as published by
### the Free Software Foundation; either version 2 of the License, or
### (at your option) any later version.
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
import rcformat
import rccommand

###
### Useful channel-related subroutines
###

cached_channel_list = []

def get_channels(server):
    global cached_channel_list
    if not cached_channel_list:
        cached_channel_list = server.rcd.packsys.get_channels()
    return cached_channel_list

def channel_to_str(c):
    return "'" + c["name"] + "' (ID# " + str(c["id"]) + ")"

def get_channel_by_id(server, id):
    channels = get_channels(server)
    for c in channels:
        if str(c["id"]) == str(id):
            return c

def channel_id_to_name(server, id):
    channels = get_channels(server)
    for c in channels:
        if str(c["id"]) == str(id):
            return c["name"]


###
### Channel-related commands
###

class ListChannelsCmd(rccommand.RCCommand):

    def name(self):
        return "channels"

    def local_opt_table(self):
        return [["s", "subscribed", "", "Only list subscribed channels"],
                ["u", "unsubscribed", "", "Only list unsubscribed channels"]]

    def execute(self, server, options_dict, non_option_args):

        channels = get_channels(server)
        channel_table = []

        for c in channels:

            show = 1

            if c["subscribed"]:
                subflag = " Yes "
                if options_dict.has_key("unsubscribed"):
                    show = 0
            else:
                subflag = ""
                if options_dict.has_key("subscribed"):
                    show = 0

            if show:
                channel_table.append([subflag, str(c["id"]), c["name"]])

        if channel_table:
            channel_table.sort(lambda x, y:cmp(x[2],y[2]))
            rcformat.tabular(["subd?", "ID", "Name"], channel_table)
        else:
            if options_dict.has_key("unsubscribed"):
                print "--- No unsubscribed channels ---"
            elif options_dict.has_key("subscribed"):
                print "--- No subscribed channels ---"
            else:
                print "--- No channels available ---"


class SubscribeCmd(rccommand.RCCommand):

    def name(self):
        return "subscribe"

    def local_opt_table(self):
        return [["s", "strict", "", "Fail if attempting to subscribe to an already-subscribed channel"]]

    def execute(self, server, options_dict, non_option_args):

        failed = 0
        for a in non_option_args:
            c = get_channel_by_id(server, a)
            if not c:
                print "Invalid channel: '" + a + "'"
                failed = 1
            elif options_dict.has_key("strict") and c["subscribed"]:
                print "Already subscribed to channel "+channel_to_str(c)
                failed = 1

        if failed:
            sys.exit(1)

        for a in non_option_args:
            c = get_channel_by_id(server, a)
            if c and server.rcd.packsys.subscribe(int(a)):
                print "Subscribed to channel '"+channel_to_str(c)


class UnsubscribeCmd(rccommand.RCCommand):

    def name(self):
        return "unsubscribe"

    def local_opt_table(self):
        return [["s", "strict", "", "Fail if attempting to unsubscribe from a non-subscribed channel"]]


    def execute(self, server, options_dict, non_option_args):

        failed = 0
        for a in non_option_args:
            c = get_channel_by_id(server, a)
            if not c:
                print "Invalid channel id: '" + a + "'"
                failed = 1
            elif options_dict.has_key("strict") and not c["subscribed"]:
                print "Not subscribed to channel "+channel_to_str(c)
                failed = 1

        if failed:
            sys.exit(1)

        for a in non_option_args:
            c = get_channel_by_id(server, a)
            if c and server.rcd.packsys.unsubscribe(int(a)):
                print "Unsubscribed to channel '"+c["name"]+"' (ID# "+str(c["id"])+")"





rccommand.register(ListChannelsCmd, "List available channels")
rccommand.register(SubscribeCmd, "Subscribe to a channel")
rccommand.register(UnsubscribeCmd, "Unsubscribe from a channel")
