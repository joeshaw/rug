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
import rctalk
import rcfault
import rcformat
import rccommand
import rcchannelutils
import ximian_xmlrpclib

class ListChannelsCmd(rccommand.RCCommand):

    def name(self):
        return "channels"

    def aliases(self):
        return ["ch"]

    def is_basic(self):
        return 1

    def category(self):
        return "channel"

    def arguments(self):
        return ""

    def description_short(self):
        return "List available channels"

    def local_opt_table(self):
        return [["s", "subscribed", "", "Only list subscribed channels"],
                ["u", "unsubscribed", "", "Only list unsubscribed channels"],
                ["m", "mounted", "", "Only list channels from mounted directories"],
                ["", "show-ids", "", "Show channel IDs"]]

    def local_orthogonal_opts(self):
        return [["subscribed", "unsubscribed"]]

    def execute(self, server, options_dict, non_option_args):

        channels = rcchannelutils.get_channels(server)
        channel_table = []

        headers = ["subd?", "Alias", "Name"]
        if options_dict.has_key("show-ids"):
            headers.insert(2, "ID")

        for c in channels:

            show = 1

            if c["hidden"]:
                show = 0

            if c["subscribed"]:
                if rctalk.be_terse:
                    subflag = "Yes"
                else:
                    subflag = " Yes "
                if options_dict.has_key("unsubscribed"):
                    show = 0
            else:
                subflag = ""
                if options_dict.has_key("subscribed"):
                    show = 0

            if show:
                row = [subflag, rcchannelutils.get_channel_alias(c), c["name"]]
                if options_dict.has_key("show-ids"):
                    row.insert(2, c["id"])
                channel_table.append(row)

        if channel_table:
            channel_table.sort(lambda x, y:cmp(x[2],y[2]))
            rcformat.tabular(headers, channel_table)
        else:
            if options_dict.has_key("unsubscribed"):
                rctalk.message("--- No unsubscribed channels ---")
            elif options_dict.has_key("subscribed"):
                rctalk.message("--- No subscribed channels ---")
            elif options_dict.has_key("mounted"):
                rctalk.message("--- No mounted channels ---")
            else:
                rctalk.warning("--- No channels available ---")


class SubscribeCmd(rccommand.RCCommand):

    def name(self):
        return "subscribe"

    def aliases(self):
        return ["sub"]

    def is_basic(self):
        return 1

    def category(self):
        return "channel"

    def arguments(self):
        return "<channel> <channel> ..."

    def description_short(self):
        return "Subscribe to a channel"

    def local_opt_table(self):
        return [["s", "strict", "", "Fail if attempting to subscribe to an already-subscribed channel"]]

    def execute(self, server, options_dict, non_option_args):

        failed = 0
        to_do = []
        for a in non_option_args:
            clist = rcchannelutils.get_channels_by_name(server, a)
            if not rcchannelutils.validate_channel_list(a, clist):
                failed = 1
            else:
                c = clist[0]
                to_do.append(c)
                if options_dict.has_key("strict") and c["subscribed"]:
                    rctalk.error("Already subscribed to channel " + \
                                 rcchannelutils.channel_to_str(c))
                    failed = 1

        if failed:
            sys.exit(1)

        for c in to_do:
            if c:
                if server.rcd.packsys.subscribe(c["id"]):
                    rctalk.message("Subscribed to channel " + \
                                   rcchannelutils.channel_to_str(c))
                else:
                    rctalk.warning("Attempt to subscribe to channel " + \
                                   rcchannelutils.channel_to_str(c) + " failed")


class UnsubscribeCmd(rccommand.RCCommand):

    def name(self):
        return "unsubscribe"

    def aliases(self):
        return ["unsub"]

    def is_basic(self):
        return 1

    def category(self):
        return "channel"

    def arguments(self):
        return "<channel> <channel> ..."

    def description_short(self):
        return "Unsubscribe from a channel"

    def local_opt_table(self):
        return [["s", "strict", "", "Fail if attempting to unsubscribe from a non-subscribed channel"]]


    def execute(self, server, options_dict, non_option_args):

        failed = 0
        to_do = []
        for a in non_option_args:
            clist = rcchannelutils.get_channels_by_name(server, a)
            if not rcchannelutils.validate_channel_list(a, clist):
                failed = 1
            else:
                c = clist[0]
                to_do.append(c)
                if options_dict.has_key("strict") and not c["subscribed"]:
                    rctalk.error("Not subscribed to channel " + \
                                 rcchannelutils.channel_to_str(c))
                    failed = 1

        if failed:
            sys.exit(1)

        for c in to_do:
            if c:
                if server.rcd.packsys.unsubscribe(c["id"]):
                    rctalk.message("Unsubscribed from channel " + \
                                   rcchannelutils.channel_to_str(c))
                else:
                    rctalk.warning("Attempt to unsubscribe to channel " + \
                                   rcchannelutils.channel_to_str(c) + " failed")


class RefreshChannelCmd(rccommand.RCCommand):

    def name(self):
        return "refresh"

    def aliases(self):
        return ["ref"]

    def category(self):
        return "system"

    def arguments(self):
        return "<channel> <channel> ..."

    def description_short(self):
        return "Refresh channel data"

    def execute(self, server, options_dict, non_option_args):

        channels = []

        # if channels is empty, that means refresh all channels.
        if non_option_args:
            failed = 0
            
            for a in non_option_args:
                clist = rcchannelutils.get_channels_by_name(server, a)
                if not rcchannelutils.validate_channel_list(a, clist):
                    failed = 1
                else:
                    channels.append(clist[0])

            if failed:
                sys.exit(1)

        rcchannelutils.refresh_channels(server, channels)

rccommand.register(ListChannelsCmd)
rccommand.register(SubscribeCmd)
rccommand.register(UnsubscribeCmd)
rccommand.register(RefreshChannelCmd)
