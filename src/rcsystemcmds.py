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
import os
import socket
import errno
import time

import rcchannelutils
import rctalk
import rcformat
import rccommand
import ximian_xmlrpclib
import rcfault

class PingCmd(rccommand.RCCommand):

    def name(self):
        return "ping"

    def description_short(self):
        return "Ping the daemon"

    def category(self):
        return "system"

    def execute(self, server, options_dict, non_option_args):

        results = server.rcd.system.ping ()

        if results:
            rctalk.message("Daemon identified itself as:")

            if results.has_key("name"):
                rctalk.message("  " + results["name"])
            else:
                rctalk.warning("Server did not return a name.")

            if results.has_key("copyright"):
                rctalk.message("  " + results["copyright"])
            else:
                rctalk.warning("Daemon did not return copyright information.")

            if results.has_key("distro_info"):
                rctalk.message("  System type: " + results["distro_info"])
            else:
                rctalk.warning("Daemon did not return system type information.")

            rctalk.message("")

            if results.has_key("server_url"):
                rctalk.message("  Server URL: " + results["server_url"])
            else:
                rctalk.warning("Daemon did not return server URL")

            if results.has_key("server_premium"):
                if results["server_premium"]:
                    rctalk.message("  Server supports enhanced features.")
            else:
                rctalk.warning("Daemon did not return server type")

            # Exit normally if we could ping the server
            sys.exit(0)

        # And exit abnormally if we couldn't.
        sys.exit(1)

rccommand.register(PingCmd)

class ShutdownCmd(rccommand.RCCommand):

    def name(self):
        return "shutdown"

    def description_short(self):
        return "Shut down the server"

    def category(self):
        return "system"

    def execute(self, server, options_dict, non_option_args):
        server.rcd.system.shutdown()

        rctalk.message("Waiting for daemon to shut down...")

        while 1:
            try:
                server.rcd.system.ping()
            except socket.error, e:
                eno, str = e
                if eno == errno.ENOENT or eno == errno.ECONNREFUSED:
                    rctalk.message("Daemon shut down.")
                    sys.exit(0)
                else:
                    raise
            except ximian_xmlrpclib.ProtocolError, e:
                if e.errcode == -1:
                    rctalk.message("Daemon shut down.")
                    sys.exit(0)
                else:
                    raise
                
            time.sleep(0.4)

rccommand.register(ShutdownCmd)

class ActivateCmd(rccommand.RCCommand):

    def name(self):
        return "activate"

    def aliases(self):
        return ["act"]

    def arguments(self):
        return "<activation code> <email address>"

    def description_short(self):
        return "Activates the machine against a premium server"

    def category(self):
        return "system"

    def local_opt_table(self):
        return [["a", "alias", "alias", "Use \"alias\" to name this machine"],
                ["n", "no-refresh", "", "Don't refresh channel data after a successful activation"]]

    def execute(self, server, options_dict, non_option_args):
        if len(non_option_args) < 2:
            self.usage()
            sys.exit(1)

        err_str = None

        try:
            if options_dict.has_key("alias"):
                success = server.rcd.system.activate_with_alias(non_option_args[0],
                                                                non_option_args[1],
                                                                options_dict["alias"])
            else:
                success = server.rcd.system.activate(non_option_args[0],
                                                     non_option_args[1])
        except ximian_xmlrpclib.Fault, f:
            if f.faultCode == rcfault.undefined_method:
                if options_dict.has_key("alias"):
                    rctalk.error("This daemon does not support activation with aliases")
                else:
                    rctalk.error("This daemon does not support activation")
                sys.exit(1)
            elif f.faultCode == rcfault.cant_activate:
                err_str = f.faultString
                success = 0
            else:
                raise

        if success:
            rctalk.message("System successfully activated")

            if not options_dict.has_key("no-refresh"):
                rcchannelutils.refresh_channels(server, [])
            
        else:
            if not err_str:
                err_str = "Invalid activation code or email address"
            
            rctalk.warning("System could not be activated: %s" % err_str)
            sys.exit(1)

rccommand.register(ActivateCmd)


class RecurringCmd(rccommand.RCCommand):

    def name(self):
        return "recurring"

    def aliases(self):
        return ["rec"]

    def description_short(self):
        return "List information about recurring events"

    def category(self):
        return "system"

    def execute(self, server, options_dict, non_option_args):

        try:
            items = server.rcd.system.get_recurring()
        except ximian_xmlrpclib.Fault, f:
            if f.faultCode == rcfault.undefined_method:
                rctalk.error("Server does not support 'recurring'.")
                sys.exit(1)
            else:
                raise
            
        items.sort(lambda x, y: cmp(x["when"], y["when"]))

        table = []
        for rec in items:
            next_str = "%s (%s)" % (rec["when_str"],
                                    rcformat.seconds_to_str(rec["when_delta"]))
            if rec.has_key("prev_str"):
                prev_str = "%s (%s)" % (rec["prev_str"],
                                        rcformat.seconds_to_str(rec["prev_delta"]))
            else:
                prev_str = ""
                
            row = []
            row.append(rec["label"])
            row.append(str(rec["count"]))
            row.append(next_str)
            row.append(prev_str)
            table.append(row)

        if table:
            rcformat.tabular(["Label", "#", "Next", "Previous"], table)
        else:
            rctalk.message("*** No recurring events are scheduled. ***")

rccommand.register(RecurringCmd)
