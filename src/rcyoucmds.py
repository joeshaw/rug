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

class ListYouPatchesCmd(rccommand.RCCommand):

    def name(self):
        return "patch-list"

    def aliases(self):
        return ["pl"]

    def description_short(self):
        return "List YOU patches"

    def category(self):
        return "YOU patches"

    def execute(self, server, options_dict, non_option_args):
        list = server.rcd.you.list ()

        if not list:
            rctalk.message("--- No Patches found ---")
            sys.exit(1)

        table = []
        for patch in list:
            installed = ""
            if patch['installed']:
                installed = "i"

            c = rcchannelutils.get_channel_by_id(server, patch['channel'])
            if c:
                channel = rcchannelutils.get_channel_alias(c)
            else:
                channel = "(None)"

            table.append((installed,
                          channel,
                          patch['name'],
                          rcformat.evr_to_str(patch)))

        table.sort(lambda x,y:cmp(x[1], y[1]))
        rcformat.tabular(["S", "Channel", "Name", "Version"], table)

rccommand.register(ListYouPatchesCmd)

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

    def execute(self, server, options_dict, non_option_args):
        if not non_option_args:
            self.usage()
            sys.exit(1)

        list = server.rcd.you.list ()
        patches = {}

        for a in non_option_args:
            for p in list:
                if p['name'] == a:
                    patches[a] = p
                    break

        for a in non_option_args:
            if not patches.has_key(a):
                rctalk.warning("Patch '%s' not found" % a)
                continue

            p = patches[a]
            rctalk.message("Name: %s" % p['name'])
            rctalk.message("Version: %s" % p['version'])

            installed = "no"
            if p['installed']:
                installed = "yes"

            rctalk.message("Installed: %s" % installed)
            rctalk.message("Summary: %s" % p['summary'])
            rctalk.message("Description:\n%s" % p['description'])
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
        return "<patch-name>"

    def local_opt_table(self):
        opts = [["N", "dry-run", "", "Do not actually perform requested actions"],
                ["u", "allow-unsubscribed", "", "Include unsubscribed channels when searching for software"],
                ["d", "download-only", "", "Only download packages, don't install them"],
                ["", "entire-channel", "", "Install all of the packages in the channels specified on the command line"]]

        return opts

    def check_licenses(self, patches):
        licenses = []
        for p in patches:
            if p.has_key("license") and len(p["license"]) > 0:
                licenses.append(p["license"])

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

    def poll_transaction(self, server, download_id, step_id):

        transact_id = -1
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
                    v = server.rcd.packsys.abort_download(download_id)
                    if v:
                        sys.exit(1)
                    else:
                        rctalk.warning("Transaction cannot be cancelled")
                else:
                    rctalk.warning("Transaction cannot be cancelled")


    def execute(self, server, options_dict, non_option_args):
        if not non_option_args:
            self.usage()
            sys.exit(1)

        if options_dict.has_key("dry-run"):
            flags = rcmain.DRY_RUN
        elif options_dict.has_key("download_only"):
            flags = rcmain.DOWNLOAD_ONLY
        else:
            flags = 0

        install_list = []

        for inst in non_option_args:
            try:
                patch = server.rcd.you.search ({"name" : inst})
            except ximian_xmlrpclib.Fault, e:
                if e.faultCode == rcfault.package_not_found:
                    rctalk.warning ("Patch '%s' not found" % inst)
                    continue
                else:
                    rctalk.error ("Unknown error: %s" % e.faultString)
                    sys.exit(1)

            if patch["installed"]:
                rctalk.warning ("Patch '%s' already installed, ignoring" % \
                                patch["name"])
            else:
                install_list.append (patch)

        if install_list:
            self.check_licenses (install_list)
            download_id, step_id = server.rcd.you.install (install_list,
                                                           flags,
                                                           "",
                                                           rcmain.rc_name,
                                                           rcmain.rc_version)

            self.poll_transaction(server, download_id, step_id)


rccommand.register(InstallYouPatchCmd)
