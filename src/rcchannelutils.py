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
import time

import rcformat
import rctalk
import rcfault

import ximian_xmlrpclib

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
        if c["id"] == id:
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

    # Make a first pass through the channels, looking for matches.
    for c in channels:
        match = 0

        chan_name = string.lower(c["name"])
        chan_alias = string.lower(get_channel_alias(c))
        
        chan_initials = reduce(lambda x,y:x+y,
                               map(lambda x:x[0],
                                   string.split(string.replace(chan_name, ".", " "))))
        chan_initials_alt = reduce(lambda x,y:x+y,
                                   map(lambda x:x[0],
                                       string.split(chan_name)))

        if c["id"] == s \
           or (chan_alias and chan_alias == s) \
           or string.find(chan_name, s) == 0 \
           or chan_initials == s \
           or chan_initials_alt == s \
           or s in string.split(chan_name):
            matches.append(c)

    # If we found more than one match, make a second pass and look for
    # exact matches on the name or alias.  If we find an exact match,
    # drop the other matches and just use the exact match.
    if len(matches) > 1:
        for c in matches:
            chan_name = string.lower(c["name"])
            chan_alias = string.lower(get_channel_alias(c))
            if s == chan_name or s == chan_alias:
                matches = [c]
                break

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
       and name != chan_list[0]["id"]:
        if not rctalk.be_terse:
            rctalk.message("'" + name + "' matches '" + cname + "'")

    return 1


def channel_id_to_name(server, id):
    channels = get_channels(server)
    for c in channels:
        if c["id"] == id:
            return c["name"]
    return ""


def add_channel_name(server, pkg):
    if pkg.has_key("channel_guess"):
        id = pkg["channel_guess"]
    else:
        id = pkg["channel"]
    pkg["channel_name"] = channel_id_to_name(server, id)

    
def refresh_channels(server, service=None):
    stuff_to_poll = []

    try:
        if service:
            stuff_to_poll = server.rcd.service.refresh(service)
        else:
            stuff_to_poll = server.rcd.service.refresh()
    except ximian_xmlrpclib.Fault, f:
        if f.faultCode == rcfault.locked:
            rctalk.error("The daemon is busy processing another "
                         "request.")
            rctalk.error("Please try again shortly.")
            sys.exit(1)
        elif f.faultCode == rcfault.cant_refresh:
            rctalk.error("Error trying to refresh: " +
                         f.faultString)
            sys.exit(1)
        elif f.faultCode == rcfault.invalid_service:
            rctalk.error("No service matches '%s'" % service)
            sys.exit(1)
        else:
            raise
        rctalk.message("Refreshing channel data")

    if stuff_to_poll:
        try:
            polling = 1
            while polling:
                polling = 0
                percent = 0

                time_remaining = -1
                for tid in stuff_to_poll:
                    pending = server.rcd.system.poll_pending(tid)

                    if pending.get("is_active", 0):
                        polling = 1

                        percent = percent + pending["percent_complete"]

                        if pending.has_key("remaining_sec"):
                            time_remaining = max(time_remaining,
                                                 pending["remaining_sec"])
                    else:
                        percent = percent + 100

                percent = percent / len(stuff_to_poll)

                msg = "Downloading... %.f%% complete" % percent
                if time_remaining >= 0:
                    msg = msg + ", " + rcformat.seconds_to_str(time_remaining) + " remaining"

                rctalk.message_status(msg)

                if polling:
                    time.sleep(0.4)

        except KeyboardInterrupt:

            rctalk.message_finished("The download will finish in the background")
            sys.exit(0)

    rctalk.message_finished("Refresh complete")

