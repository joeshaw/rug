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
import re
import rctalk
import rcformat
import rccommand
import ximian_xmlrpclib

entity_dict = { "copy":"(C)",
                "reg":"(R)" }

entity_regex = re.compile("\&\w+\;")

def textify_entities(in_str):
    s = in_str
    while 1:
        x = entity_regex.search(s)
        if not x:
            return s
        i = x.start(0)
        j = x.end(0)
        entity = s[i+1:j-1]
        if entity and entity_dict.has_key(entity):
            entity = entity_dict[entity]
        else:
            entity = "("+entity+")"
        s = s[:i] + entity + s[j:]

class NewsCmd(rccommand.RCCommand):

    def name(self):
        return "news"

    def arguments(self):
        return ""

    def description_short(self):
        return "Show Red Carpet news"

    def local_opt_table(self):
        return [["c", "channel", "channel",    "Show news related to a specific channel"],
                ["s", "subscribed-only", "",   "Only show news related to subscribed channels"],
                ["u", "unsubscribed-only", "", "Only show news related to unsubscribed channels."]]

    def local_orthogonal_opts(self):
        return [["channel", "subscribed-only", "unsubscribed-only"]]

    def execute(self, server, options_dict, non_option_args):

        ### For now, we just do something pretty mindless

        ### FIXME: the channel selection aren't supported yet

        news = server.rcd.news.get_all()

        if not news:
            rctalk.message("--- No news available ---")
            sys.exit(0)

        for n in news:
            if n.has_key("server"):
                rctalk.message("[%s]" % n["server"])
            if n.has_key("title"):
                rctalk.message(textify_entities(n["title"]))
            if n.has_key("time_str"):
                rctalk.message("("+n["time_str"]+")")
            if n.has_key("summary"):
                summary = re.sub("\s+", " ", n["summary"])
                lines = rcformat.linebreak(textify_entities(summary), 75)
                for l in lines:
                    rctalk.message(l)
            if n.has_key("url"):
                rctalk.message("To learn more, visit " + n["url"])
            rctalk.message("")


rccommand.register(NewsCmd)

