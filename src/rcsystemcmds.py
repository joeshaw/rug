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
import rctalk
import rcformat
import rccommand

class PingCmd(rccommand.RCCommand):

    def name(self):
        return "ping"

    def description_short(self):
        return "Ping the server"

    def execute(self, server, options_dict, non_option_args):

        results = server.rcd.system.ping ()

        if results:
            rctalk.message("Server identified itself as:")

            if results.has_key("name"):
                rctalk.message("  " + results["name"])
            else:
                rctalk.warning("Server did not return a name.")

            if results.has_key("copyright"):
                rctalk.message("  " + results["copyright"])
            else:
                rctalk.warning("Server did not return copyright information.")

            # Exit normally if we could ping the server
            sys.exit(0)

        # And exit abnormally if we couldn't.
        sys.exit(1)

rccommand.register(PingCmd)

