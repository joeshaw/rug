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
import re
import rctalk

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
    return "'" + c["name"] + "'"

def get_channel_by_id(server, id):
    channels = get_channels(server)
    for c in channels:
        if str(c["id"]) == str(id):
            return c

def check_subscription_by_id(server, id):
    c = get_channel_by_id(server, id)
    return c and c["subscribed"]

def get_channel_alias(c):
    alias = c["alias"]
    if not alias:
        alias = string.strip(string.lower(c["name"]))
        alias = string.replace(alias, " ", "-")
        
        # FIXME: hackish evil to generate nicer fallback aliases.
        # This should be removed once we actually get aliases
        # into the channel XML.
        alias = re.sub("-devel[a-z]*-", "-dev-", alias)
        alias = re.sub("snapshots?", "snaps", alias)
        alias = string.replace(alias, "gnome-2.0", "gnome2")
        alias = string.replace(alias, "evolution", "evo")
        alias = string.replace(alias, "-gnome-", "-")
        if string.find(alias, "red-hat") == 0:
          alias = "redhat"
            
    return alias

def get_channels_by_name(server, in_str):
    channels = get_channels(server)
    matches = []

    s = string.lower(in_str)

    for c in channels:
        match = 0

        chan_name = string.lower(c["name"])
        chan_alias = get_channel_alias(c)
        
        chan_initials = reduce(lambda x,y:x+y,
                               map(lambda x:x[0],
                                   string.split(string.replace(chan_name, ".", " "))))
        chan_initials_alt = reduce(lambda x,y:x+y,
                                   map(lambda x:x[0],
                                       string.split(chan_name)))

        if str(c["id"]) == s \
           or (chan_alias and chan_alias == s) \
           or string.find(chan_name, s) == 0 \
           or chan_initials == s \
           or chan_initials_alt == s \
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
    return ""


def add_channel_name(server, pkg):
    if pkg.has_key("channel_guess"):
        id = pkg["channel_guess"]
    else:
        id = pkg["channel"]
    pkg["channel_name"] = channel_id_to_name(server, id)

    

