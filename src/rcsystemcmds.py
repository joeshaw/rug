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

            # Exit normally if we could ping the server
            return

        # And exit abnormally if we couldn't.
        sys.exit(1)

rccommand.register(PingCmd)

class ShutdownCmd(rccommand.RCCommand):

    def name(self):
        return "shutdown"

    def description_short(self):
        return "Shut down the daemon"

    def category(self):
        return "system"

    # This API will never change, so setting this to local prevents checking
    # the protocol version.  We want to be able to shut down no matter what.
    def is_local(self):
        return 1

    def local_opt_table(self):
        return [["n", "no-wait", "", "Don't wait for confirmation that the daemon was shut down"]]

    def execute(self, server, options_dict, non_option_args):
        server.rcd.system.shutdown()

        if options_dict.has_key("no-wait"):
            sys.exit(0)

        rctalk.message("Waiting for daemon to shut down...")

        while 1:
            try:
                server.rcd.system.ping()
            except socket.error, e:
                eno, str = e
                if eno == errno.ENOENT \
                       or eno == errno.ECONNREFUSED \
                       or eno == errno.ECONNRESET:
                    rctalk.message("Daemon shut down.")
                    sys.exit(0)
                else:
		    print eno
                    print str
                    raise
            except ximian_xmlrpclib.ProtocolError, e:
                if e.errcode == -1:
                    rctalk.message("Daemon shut down.")
                    sys.exit(0)
                else:
                    raise
                
            time.sleep(0.4)

rccommand.register(ShutdownCmd)

class RestartCmd(rccommand.RCCommand):

    def name(self):
        return "restart"

    def description_short(self):
        return "Restart the daemon"

    def category(self):
        return "system"

    # This API will never change, so setting this to local prevents checking
    # the protocol version.  We want to be able to restart no matter what.
    def is_local(self):
        return 1

    def local_opt_table(self):
        return [["n", "no-wait", "", "Don't wait for confirmation that the daemon has restarted"]]

    def execute(self, server, options_dict, non_option_args):
        server.rcd.system.restart()

        if options_dict.has_key("no-wait"):
            sys.exit(0)

        rctalk.message("Waiting for daemon to restart...")

        is_down = 0
        while 1:
            try:
                server.rcd.system.ping()
            except socket.error, e:
                eno, str = e
                if eno == errno.ENOENT \
                       or eno == errno.ECONNREFUSED \
                       or eno == ernno.ECONNRESET:
                    is_down = 1
                else:
                    raise
            except ximian_xmlrpclib.ProtocolError, e:
                if e.errcode == -1:
                    is_down = 1
                else:
                    raise
            else:
                if is_down:
                    rctalk.message("Daemon restarted successfully.")
                    sys.exit(0)
                
            time.sleep(0.4)

rccommand.register(RestartCmd)

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
            if rec["when_delta"] > 0:
                when_delta = rcformat.seconds_to_str(rec["when_delta"])
            else:
                when_delta = "running"
            next_str = "%s (%s)" % (rec["when_str"], when_delta)

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

