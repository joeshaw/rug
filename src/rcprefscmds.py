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

import rctalk
import rcformat
import rccommand
import rcmain
import ximian_xmlrpclib

class PrefsCmd(rccommand.RCCommand):

    def name(self):
        return "preferences"

    def aliases(self):
        return ["prefs"]

    def arguments(self):
        return "some stuff..."

    def description_short(self):
        return "List, get, and set system preferences"

    def execute(self, server, options_dict, non_option_args):
        headers = ["Name", "Value"]
        pref_table = []
        
        if not non_option_args:
            pref_table = map(lambda p:[p["name"], str(p["value"])],
                             server.rcd.prefs.list_prefs())
        else:
            for a in non_option_args:
                try:
                    p = server.rcd.prefs.get_pref(a)
                except ximian_xmlrpclib.Fault, f:
                    if f.faultCode == -630:
                        rctalk.warning("There is no preference named '" + a + "'")
                    else:
                        raise
                else:
                    pref_table.append([a, str(p)])

        if pref_table:
            rcformat.tabular(headers, pref_table)

rccommand.register(PrefsCmd)
            
