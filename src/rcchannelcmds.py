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

def get_channels_by_name(server, in_str):
    channels = get_channels(server)
    matches = []

    s = string.lower(in_str)

    for c in channels:
        match = 0

        chan_name = string.lower(c["name"])
        chan_initials = reduce(lambda x,y:x+y,
                               map(lambda x:x[0],
                                   string.split(string.replace(chan_name, ".", " "))))

        if str(c["id"]) == s \
           or string.find(chan_name, s) == 0 \
           or chan_initials == s \
           or s in string.split(chan_name):
            matches.append(c)

    return matches

# Given a string and a list of channels returned by get_channels_by_name,
# print appropriate messages if our list has anything other than a single
# item that closely matches the string.
def validate_channel_list(name, chan_list):

    if len(chan_list) == 0:
        rctalk.warning("Invalid channel: '" + name + "'")
        return 0
    elif len(chan_list) > 1:
        rctalk.warning("Ambiguous channel: '" + name + "' matches")
        for c in chan_list:
            rctalk.warning("  " + c["name"])
        return 0

    cname = chan_list[0]["name"]
    if string.lower(name) != string.lower(cname) \
       and name != str(chan_list[0]["id"]):
        rctalk.message("'" + name + "' matches '" + cname + "'")

    return 1


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
                rctalk.message("--- No unsubscribed channels ---")
            elif options_dict.has_key("subscribed"):
                rctalk.message("--- No subscribed channels ---")
            else:
                rctalk.warning("--- No channels available ---")


class SubscribeCmd(rccommand.RCCommand):

    def name(self):
        return "subscribe"

    def local_opt_table(self):
        return [["s", "strict", "", "Fail if attempting to subscribe to an already-subscribed channel"]]

    def execute(self, server, options_dict, non_option_args):

        failed = 0
        to_do = []
        for a in non_option_args:
            clist = get_channels_by_name(server, a)
            if not validate_channel_list(a, clist):
                failed = 1
            else:
                c = clist[0]
                to_do.append(c)
                if options_dict.has_key("strict") and c["subscribed"]:
                    rctalk.error("Already subscribed to channel "+channel_to_str(c))
                    failed = 1

        if failed:
            sys.exit(1)

        for c in to_do:
            if c and server.rcd.packsys.subscribe(c["id"]):
                rctalk.message("Subscribed to channel "+channel_to_str(c))


class UnsubscribeCmd(rccommand.RCCommand):

    def name(self):
        return "unsubscribe"

    def local_opt_table(self):
        return [["s", "strict", "", "Fail if attempting to unsubscribe from a non-subscribed channel"]]


    def execute(self, server, options_dict, non_option_args):

        failed = 0
        to_do = []
        for a in non_option_args:
            clist = get_channels_by_name(server, a)
            if not validate_channel_list(a, clist):
                failed = 1
            else:
                c = clist[0]
                to_do.append(c)
                if options_dict.has_key("strict") and not c["subscribed"]:
                    rctalk.error("Not subscribed to channel "+channel_to_str(c))
                    failed = 1

        if failed:
            sys.exit(1)

        for c in to_do:
            if c and server.rcd.packsys.unsubscribe(c["id"]):
                rctalk.message("Unsubscribed from channel "+channel_to_str(c))


class RefreshChannelCmd(rccommand.RCCommand):

    def name(self):
        return "refresh"

    def execute(self, server, options_dict, non_option_args):

        if not non_option_args:
            server.rcd.packsys.refresh_all_channels()
            rctalk.message("Refreshing all channels")
        else:
            failed = 0
            to_do = []
            
            for a in non_option_args:
                clist = get_channels_by_name(server, a)
                if not validate_channel_list(a, clist):
                    failed = 1
                else:
                    to_do.append(clist[0])

            if failed:
                sys.exit(1)

            for c in to_do:
                if c and server.rcd.packsys.refresh_channel(int(c["id"])):
                    print "Refreshing channel "+channel_to_str(c)

rccommand.register(ListChannelsCmd, "List available channels")
rccommand.register(SubscribeCmd, "Subscribe to a channel")
rccommand.register(UnsubscribeCmd, "Unsubscribe from a channel")
rccommand.register(RefreshChannelCmd, "Refresh channel data")
