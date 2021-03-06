###
### Copyright 2002-2003 Ximian, Inc.
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

import errno
import os
import re
import string
import sys

import rcfault
import rcformat
import rcchannelutils
import rcmain
import rctalk
import ximian_xmlrpclib

def split_channel_and_name(server, s):
    # Try to split the string into "channel:name"
    off = string.find(s, ":")
    if off != -1:
        channel = s[:off]
        name = s[off+1:]
    else:
        channel = None
        name = s

    # Validate the channel
    if channel:
        clist = rcchannelutils.get_channels_by_name(server, channel)

        if not rcchannelutils.validate_channel_list(channel, clist):
            sys.exit(1)
            
        channel_id = clist[0]["id"]
    else:
        channel_id = None

    return (channel_id, name)

# This isn't the most efficient way of doing things, but we need to do it
# because rcd.packsys.find_latest_version() doesn't do globbing.  So we
# need to get the list of all of the packages that match our glob and
# then check to see if it's valid and newer than what we already have.
def find_latest_package(server, package, allow_unsub, quiet):
    plist = server.rcd.packsys.search([["name", "is", package],
                                       ["installed", "is", "false"]])

    if not plist:
        if not quiet:
            if allow_unsub:
                rctalk.error("Unable to find package '" + package + "'")
            else:
                rctalk.error("Unable to find package '" + package +
                             "' in any subscribed channel")
        return []

    pkeys = {}
    pl = []

    for p in plist:
        if not pkeys.has_key(p["name"]):
            latest_p = get_latest_version(server, p["name"],
                                          allow_unsub, quiet)
            if latest_p:
                pl.append(latest_p)

            pkeys[p["name"]] = p

    return pl

def get_latest_version(server, package, allow_unsub, quiet):
    try:
        if allow_unsub:
            b = ximian_xmlrpclib.False
        else:
            b = ximian_xmlrpclib.True

        p = server.rcd.packsys.find_latest_version(package, b)
    except ximian_xmlrpclib.Fault, f:
        if f.faultCode == rcfault.package_not_found:
            if not quiet:
                if allow_unsub:
                    rctalk.error("Unable to find package '" + package + "'")
                else:
                    rctalk.error("Unable to find package '" + package +
                                 "' in any subscribed channel")
            p = None
        elif f.faultCode == rcfault.package_is_newest:
            if not quiet:
                if allow_unsub:
                    rctalk.error("There is no newer version of '" + package + "'")
                else:
                    rctalk.error("There is no newer version of '" + package +
                                 "' in any subscribed channel")
            p = None
        else:
            raise

    return p

def find_package_in_channel(server, channel, package, allow_unsub):
    plist = server.rcd.packsys.search([["name",      "is", package],
                                       ["installed", "is", "false"],
                                       ["channel",   "is", str(channel)]])

    if not plist:
        rctalk.error("Unable to find package '" + package + "'")
        return []

    return plist

def find_package_on_system(server, package):
    plist = server.rcd.packsys.search([["name",      "is", package],
                                       ["installed", "is", "true"]])

    return plist

def find_remote_package(server, package):
    try:
        import urllib
    except ImportError:
        return None

    # Figure out if the protocol is valid.  Copied mostly from urllib.
    proto, rest = urllib.splittype(package)

    if not proto:
        return None

    name = "open_" + proto
    if "-" in name:
        # replace - with _
        name = string.join(string.split(name, "-"), "_")

    if not hasattr(urllib.URLopener, name):
        return None

    rctalk.message("Fetching %s..." % package)
    u = urllib.URLopener().open(package)
    pdata = ximian_xmlrpclib.Binary(u.read())

    try:
        p = server.rcd.packsys.query_file(pdata)
    except ximian_xmlrpclib.Fault,f :
        if f.faultCode == rcfault.package_not_found:
            return None
        elif f.faultCode == rcfault.invalid_package_file:
            rctalk.warning ("'" + package + "' is not a valid package file")
            return None
        else:
            raise

    p["package_data"] = pdata

    return p

def find_local_package(server, package):
    try:
        os.stat(package)
    except OSError, e:
        eno, estr = e
        if eno == errno.ENOENT:
            # No such file or directory.
            return None
        elif eno == errno.EPERM or eno == errno.EACCES:
            # Operation not permitted / Permission denied
            return None
        else:
            raise

    if rcmain.local:
        pdata = os.path.abspath(package)
    else:
        pdata = ximian_xmlrpclib.Binary(open(package).read())

    try:
        p = server.rcd.packsys.query_file(pdata)
    except ximian_xmlrpclib.Fault, f:
        if f.faultCode == rcfault.package_not_found:
            return None
        elif f.faultCode == rcfault.invalid_package_file:
            rctalk.warning ("'" + package + "' is not a valid package file")
            return None
        else:
            raise

    if rcmain.local:
        p["package_filename"] = pdata
    else:
        p["package_data"] = pdata

    return p


def find_package(server, str, allow_unsub, allow_system=1):

    channel = None
    package = None

    # Check if the string is a file on the local filesystem.
    p = find_local_package(server, str)
    if p:
        return [p]

    # Check if the string is a supported URL
    p = find_remote_package(server, str)
    if p:
        return [p]

    # Okay, try to split the string into "channel:package"
    channel_id, package = split_channel_and_name(server, str)

    # Channel is set, so just get the package(s) from the channel.
    if channel_id:
        plist = find_package_in_channel(server, channel_id,
                                        package, allow_unsub)

        return plist

    # Okay, that didn't work.  First try to get the package from the list
    # of system packages.  After that, try to get the latest available
    # package.
    plist = []

    if allow_system:
        plist = find_package_on_system(server, package)

    if plist:
        quiet = 1
    else:
        quiet = 0

    new_plist = find_latest_package(server,
                                    package,
                                    allow_unsub,
                                    quiet)

    # Filter out packages already on the system, so we don't get both
    # the installed version of a package and the newest available
    # version.
    for p in new_plist:
        if not filter(lambda x, my_p=p:x["name"] == my_p["name"],
                      plist):
            rctalk.message("Using " + p["name"] + " " +
                           rcformat.evr_to_str(p) + " from the '" +
                           rcchannelutils.channel_id_to_name(server, p["channel"]) +
                           "' channel")
            plist.append(p)

    return plist


update_importances = {"minor"     : 4,
                      "feature"   : 3,
                      "suggested" : 2,
                      "urgent"    : 1,
                      "necessary" : 0}

def get_updates(server, non_option_args, allow_dups=0):
    up = server.rcd.packsys.get_updates()

    # If channels are specified by the command line, filter out all except
    # for updates from those channels.
    if non_option_args:
        channel_id_list = []
        failed = 0
        for a in non_option_args:
            clist = rcchannelutils.get_channels_by_name(server, a)
            if not rcchannelutils.validate_channel_list(a, clist):
                failed = 1
            else:
                c = clist[0]
                if c["subscribed"]:
                    channel_id_list.append(c["id"])
                else:
                    rctalk.warning("You are not subscribed to "
                                   + rcchannelutils.channel_to_str(c)
                                   + ", so no updates are available.")
                    
        if failed:
            sys.exit(1)

        up = filter(lambda x, cidl=channel_id_list:x[1]["channel"] in cidl, up)

    # Filter out exact duplicates
    if not allow_dups:
        def pkg_to_key(p):
            return "%s:%d:%s:%s" % \
                   (p["name"], p["epoch"], p["version"], p["release"])

        dup_dict = {}
        for u in up:
            key = pkg_to_key(u[1]) # u[1] is the new version of the package
            if not dup_dict.has_key(key):
                dup_dict[key] = u

        up = dup_dict.values()

        del dup_dict

    return up

def filter_visible_channels(server, packages):
    visible_channels = map(lambda c:c["id"],
                           filter(lambda c:not c["hidden"],
                                  rcchannelutils.get_channels(server)))

    # Return a filtered list of packages, each of which:
    #
    #  (a) is in a visible channel.
    #  (b) is not in a visible channel, but doesn't have a guessed channel
    #      (indicating that it's a system package and we don't know what
    #      channel it came from)

    return filter(lambda p:p["channel"] in visible_channels
                  or not p.has_key("channel_guess"),
                  packages)

def parse_dep_str(server, dep_str):
    dep = {}
    package = string.split(dep_str)

    if len(package) > 1:
        valid_relations = ["=", "<", "<=", ">", ">=", "!="]

        if not package[1] in valid_relations:
            rctalk.error("Invalid relation.")
            sys.exit(1)

        channel_id, name = split_channel_and_name(server, package[0])

        if channel_id:
            dep["channel"] = channel_id

        dep["name"] = name

        dep["relation"] = package[1]

        version_regex = re.compile("^(?:(\d+):)?(.*?)(?:-([^-]+))?$")
        match = version_regex.match(package[2])

        if match.group(1):
            dep["has_epoch"] = 1
            dep["epoch"] = int(match.group(1))
        else:
            dep["has_epoch"] = 0
            dep["epoch"] = 0

        dep["version"] = match.group(2)

        if match.group(3):
            dep["release"] = match.group(3)
        else:
            dep["release"] = ""
    else:
        channel_id, name = split_channel_and_name(server, dep_str)

        if channel_id:
            dep["channel"] = channel_id

        dep["name"] = name
        dep["relation"] = "(any)"
        dep["has_epoch"] = 0
        dep["epoch"] = 0
        dep["version"] = "*"
        dep["release"] = "*"
    
    return dep
