###
### Copyright 2004 Novell, Inc.
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
import os
import socket
import errno
import time
import string

import rctalk
import rcformat
import rccommand
import rcmain
import ximian_xmlrpclib
import rcfault
import rcchannelutils
import rcpackageutils

def server_has_patch_support(server):
    return server.rcd.system.query_module("rcd.you", 1, 0)

class ListYouPatchesCmd(rccommand.RCCommand):

    def name(self):
        return "patch-list"

    def aliases(self):
        return ["pl"]

    def description_short(self):
        return "List YOU patches"

    def arguments(self):
        return "<channel> <channel> ..."

    def category(self):
        return "YOU patches"

    def local_opt_table(self):
        return [["",  "no-abbrev", "", "Do not abbreviate channel or version information"],
                ["i", "installed-only", "", "Show only installed patches"],
                ["u", "uninstalled-only", "", "Show only uninstalled patches"],
                ["",  "sort-by-name", "", "Sort patches by name (default)"],
                ["",  "sort-by-channel", "", "Sort patches by channel"]]

    def execute(self, server, options_dict, non_option_args):

        if not server_has_patch_support (server):
            rctalk.error ("Current rcd daemon does not have patch support")
            sys.exit(1)

        patches = []
        patch_table = []

        multiple_channels = 1

        query = []
        clist = []

        for a in non_option_args:
            cl = rcchannelutils.get_channels_by_name(server, a)
            if rcchannelutils.validate_channel_list(a, cl):
                clist = clist + cl

        if non_option_args and not clist:
            sys.exit(1)

        query = map(lambda c:["channel", "=", c["id"]], clist)

        if len(clist) > 1:
            query.insert(0, ["", "begin-or", ""])
            query.append(["", "end-or", ""])

        if options_dict.has_key("installed-only"):
            query.append(["name-installed", "=", "true"])
        elif options_dict.has_key("uninstalled-only"):
            query.append(["patch-installed", "=", "false"])

        if len(clist) == 1:
            multiple_channels = 0

        patches = server.rcd.you.search (query)

        if options_dict.has_key("sort-by-channel"):
            for p in patches:
                rcchannelutils.add_channel_name(server, p)

            patches.sort(lambda x,y:cmp(string.lower(x["channel_name"]), string.lower(y["channel_name"])) \
                         or cmp(string.lower(x["name"]), string.lower(y["name"])))
        else:
            patches.sort(lambda x,y:cmp(string.lower(x["name"]),string.lower(y["name"])))

        if multiple_channels:
            keys = ["installed", "channel", "name", "version", "product"]
            headers = ["S", "Channel", "Name", "Version", "Product"]
        else:
            keys = ["installed", "name", "version", "product"]
            headers = ["S", "Name", "Version", "Product"]

        # If we're getting all of the packages available to us, filter out
        # ones in the "hidden" channels, like the system packages channel.
        patches = rcpackageutils.filter_visible_channels(server, patches)

        for p in patches:
            row = rcformat.package_to_row(server, p, options_dict.has_key("no-abbrev"), keys)
            patch_table.append(row)

        if patch_table:
            rcformat.tabular(headers, patch_table)
        else:
            rctalk.message("--- No Patches found ---")


rccommand.register(ListYouPatchesCmd)


def find_latest_patch(server, patch, allow_unsub, quiet):
    plist = server.rcd.you.search([["name", "is", patch],
                                   ["installed", "is", "false"]])

    if not plist:
        if not quiet:
            if allow_unsub:
                rctalk.error("Unable to find patch '%s'" % patch)
            else:
                rctalk.error("Unable to find patch '%s' in any " \
                             "subscribed channel" % patch)
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

def get_latest_version(server, patch, allow_unsub, quiet):
    try:
        if allow_unsub:
            b = ximian_xmlrpclib.False
        else:
            b = ximian_xmlrpclib.True

        p = server.rcd.you.find_latest_version(patch, b)
    except ximian_xmlrpclib.Fault, f:
        if f.faultCode == rcfault.package_not_found:
            if not quiet:
                if allow_unsub:
                    rctalk.error("Unable to find patch '%s'" % patch)
                else:
                    rctalk.error("Unable to find patch '%s' in any " \
                                 "subscribed channel" % patch)
            p = None
        elif f.faultCode == rcfault.package_is_newest:
            if not quiet:
                if allow_unsub:
                    rctalk.error("There is no newer version of '%s'" % patch)
                else:
                    rctalk.error("There is no newer version of '%s'" \
                                 "in any subscribed channel" % patch)
            p = None
        else:
            raise

    return p

def find_patch_in_channel(server, channel, patch, allow_unsub):
    plist = server.rcd.you.search([["name",      "is", patch],
                                   ["installed", "is", "false"],
                                   ["channel",   "is", str(channel)]])

    if not plist:
        rctalk.error("Unable to find patch '" + patch + "'")
        return []

    return plist

def find_patch_on_system(server, patch):
    plist = server.rcd.you.search([["name",      "is", patch],
                                   ["installed", "is", "true"]])

    return plist


def find_patch(server, str, allow_unsub, allow_system=1):

    channel = None
    patch = None

    # Try to split the string into "channel:package"
    channel_id, patch = rcpackageutils.split_channel_and_name(server, str)

    # Channel is set, so just get the patch(es) from the channel.
    if channel_id:
        plist = find_patch_in_channel(server, channel_id,
                                      patch, allow_unsub)

        return plist

    # Okay, that didn't work.  First try to get the patch from the list
    # of system patches.
    plist = []

    if allow_system:
        plist = find_patch_on_system(server, patch)

    if plist:
        quiet = 1
    else:
        quiet = 0

    new_plist = find_latest_patch(server,
                                  patch,
                                  allow_unsub,
                                  quiet)


    # Filter out patches already on the system, so we don't get both
    # the installed version of a patch and the newest available
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
    

class InfoYouPatchCmd(rccommand.RCCommand):

    def name(self):
        return "patch-info"

    def aliases(self):
        return ["pi"]

    def description_short(self):
        return "Show detailed information about a YOU patch"

    def category(self):
        return "YOU patches"

    def arguments(self):
        return "<patch-name>"

    def local_opt_table(self):
        return [["u", "allow-unsubscribed", "", "Search in unsubscribed channels as well"]]

    def execute(self, server, options_dict, non_option_args):
        if not non_option_args:
            self.usage()
            sys.exit(1)

        if not server_has_patch_support (server):
            rctalk.error ("Current rcd daemon does not have patch support")
            sys.exit(1)

        if options_dict.has_key("allow-unsubscribed"):
            allow_unsub = 1
        else:
            allow_unsub = 0

        plist = []

        for a in non_option_args:
            inform = 0
            channel = None
            package = None

            plist = plist + find_patch(server, a, allow_unsub)

        if not plist:
            rctalk.message("--- No patches found ---")
            sys.exit(1)

        for p in plist:
            pinfo = server.rcd.you.patch_info(p)

            rctalk.message("")
            rctalk.message("Name: %s" % p['name'])
            rctalk.message("Version: %s" % p['version'])

            installed = "no"
            if p['installed']:
                installed = "yes"

            rctalk.message("Installed: %s" % installed)
            rctalk.message("Summary: %s" % pinfo['summary'])
            rctalk.message("Description:\n%s" % pinfo['description'])
            rctalk.message("")

rccommand.register(InfoYouPatchCmd)


class InstallYouPatchCmd(rccommand.RCCommand):

    def name(self):
        return "patch-install"

    def aliases(self):
        return ["pin"]

    def description_short(self):
        return "Install YOU patches"

    def category(self):
        return "YOU patches"

    def arguments(self):
        return "<patch-name> ..."

    def local_opt_table(self):
        return [["u", "allow-unsubscribed", "", "Include unsubscribed channels when searching for software"],
                ["d", "download-only", "", "Only download packages, don't install them"],
                ["", "entire-channel", "", "Install all of the packages in the channels specified on the command line"]]

    def check_licenses(self, server, patches):
        try:
            licenses = server.rcd.you.licenses(patches)
        except ximian_xmlrpclib.Fault, f:
            if f.faultCode == rcfault.undefined_method:
                return
            else:
                raise
        if licenses:
            if len(licenses) > 1:
                lstr = "licenses"
            else:
                lstr = "license"
            rctalk.message("")
            rctalk.message("You must agree to the following %s before "
                           "installing this software:" % lstr)
            rctalk.message("")

            for l in licenses:
                rctalk.message(string.join(rcformat.linebreak(l, 72), "\n"))
                rctalk.message("")

            confirm = rctalk.prompt("Do you agree to the above "
                                    "%s? [y/N]" % lstr)
            if not confirm or not (confirm[0] == "y" or confirm[0] == "Y"):
                rctalk.message("Cancelled.")
                sys.exit(0)

    def poll_transaction(self, server, download_id, transact_id, step_id):

        message_offset = 0
        download_complete = 0

        while 1:
            try:
                if download_id != -1 and not download_complete:
                    pending = server.rcd.system.poll_pending(download_id)

                    rctalk.message_status(rcformat.pending_to_str(pending))

                    if pending["status"] == "finished":
                        rctalk.message_finished("Download complete")
                        download_complete = 1
                    elif pending["status"] == "failed":
                        rctalk.message_finished("Download failed: %s" % pending["error_msg"])
                        sys.exit(1)
                elif transact_id == -1:
                    # We're in "download only" mode.
                    if download_complete:
                        break
                    elif download_id == -1:
                        # We're in "download only" mode, but everything we
                        # wanted to download is already cached on the system.
                        rctalk.message_finished("Nothing to download")
                        break
                else:
                    pending = server.rcd.system.poll_pending(transact_id)
                    step_pending = server.rcd.system.poll_pending(step_id)

                    message_len = len(pending["messages"])
                    if message_len > message_offset:
                        for e in pending["messages"][message_offset:]:
                            rctalk.message_finished(rcformat.transaction_status(e))
                        message_offset = message_len

                    message_or_message_finished = rctalk.message

                    if step_pending["status"] == "running":
                        rctalk.message_status(rcformat.pending_to_str(step_pending, time=0))

                    if pending["status"] == "finished":
                        rctalk.message_finished("Transaction finished")
                        break
                    elif pending["status"] == "failed":
                        rctalk.message_finished("Transaction failed: %s" % pending["error_msg"],
                                                force_output=1)
                        sys.exit(1)

                time.sleep(0.4)
            except KeyboardInterrupt:
                if download_id != -1 and not download_complete:
                    rctalk.message("")
                    rctalk.message("Cancelling download...")
                    try:
                        v = server.rcd.you.abort_download(download_id)
                        if v:
                            sys.exit(1)
                    except ximian_xmlrpclib.Fault:
                            pass

                rctalk.warning("Transaction cannot be cancelled")


    def execute(self, server, options_dict, non_option_args):
        if not server_has_patch_support (server):
            rctalk.error ("Current rcd daemon does not have patch support")
            sys.exit(1)

        install_list = []

        if options_dict.has_key("download_only"):
            flags = rcmain.DOWNLOAD_ONLY
        else:
            flags = 0

        if options_dict.has_key("allow-unsubscribed"):
            allow_unsub = 1
        else:
            allow_unsub = 0

        if options_dict.has_key("entire-channel"):
            channel_list = []
            for a in non_option_args:
                matches = rcchannelutils.get_channels_by_name(server, a)
                if not rcchannelutils.validate_channel_list(a, matches):
                    sys.exit(1)
                channel_list.append(matches[0])

            contributors = 0
            for c in channel_list:
                query = [["channel", "=", c["id"]],
                         ["patch-installed", "=", "false"]]
                patches = server.rcd.you.search(query)
                install_list.extend(patches)
                if len(patches) > 0:
                    contributors = contributors + 1
                msg = "Found %d %s in channel '%s'" % \
                      (len(patches),
                       (len(patches) != 1 and "patches") or "patch",
                       c["name"])
                rctalk.message(msg)

            if contributors > 1:
                msg = "Found a total of %d %s" % \
                      (len(install_list),
                       (len(install_list) != 1 and "patches")
                       or "patch")
                rctalk.message(msg)

            rctalk.message("")
        else:
            for a in non_option_args:
                plist = find_patch(server, a,
                                   allow_unsub,
                                   allow_system=0)

                if not plist:
                    sys.exit(1)

                for p in plist:
                    dups = filter(lambda x, pn=p:x["name"] == pn["name"],
                                  install_list)
                    
                    if dups:
                        rctalk.error("Duplicate entry found: " +
                                     dups[0]["name"])
                        sys.exit(1)

                    install_list.append(p)

        if not install_list:
            rctalk.message("--- No patches to install ---")
            sys.exit(0)
        
        self.check_licenses (server, install_list)
        download_id, transact_id, step_id = \
                     server.rcd.you.transact (install_list,
                                              flags,
                                              "",
                                              rcmain.rc_name,
                                              rcmain.rc_version)

        self.poll_transaction(server, download_id, transact_id, step_id)


rccommand.register(InstallYouPatchCmd)
