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
import ximian_xmlrpclib

class NewsCmd(rccommand.RCCommand):

    def name(self):
        return "news"

    def local_opt_table(self):
        return [["c", "channel", "channel",    "Show news related to a specific channel"],
                ["s", "subscribed-only", "",   "Only show news related to subscribed channels"],
                ["u", "unsubscribed-only", "", "Only show news related to unsubscribed channels."]]

    def local_orthogonal_opts(self):
        return [["channel", "subscribed-only", "unsubscribed-only"]];

    def execute(self, server, options_dict, non_option_args):

        ### For now, we just do something pretty mindless

        ### FIXME: the channel selection aren't supported yet

        news = server.rcd.news.get_all()

        if not news:
            rctalk.message("--- No news available ---")
            sys.exit(0)

        for n in news:
            if n.has_key("title"):
                rctalk.message(n["title"])
            if n.has_key("time_str"):
                rctalk.message("("+n["time_str"]+")")
            if n.has_key("summary"):
                lines = rcformat.linebreak(n["summary"], 75)
                for l in lines:
                    rctalk.message(l)
            if n.has_key("url"):
                rctalk.message("To learn more, visit " + n["url"])
            rctalk.message("")


rccommand.register(NewsCmd, "Show Red Carpet news")

