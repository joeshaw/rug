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

import string
import sys
import rctalk
import rcfault
import rcformat
import rccommand
import rcchannelutils
import rcmain
import ximian_xmlrpclib

class PrefsSetCmd(rccommand.RCCommand):

    def name(self):
        return "set-prefs"

    def aliases(self):
        return ["set"]

    def arguments(self):
        return "<pref name> <value>"

    def description_short(self):
        return "Set a preference variable"

    def category(self):
        return "prefs"

    def execute(self, server, options_dict, non_option_args):
        if len(non_option_args) < 2:
            self.usage()
            sys.exit(0)

        try:
            pref = server.rcd.prefs.get_pref(non_option_args[0])
        except ximian_xmlrpclib.Fault, f:
            if f.faultCode == rcfault.invalid_preference:
                rctalk.error("There is no preference named '" + non_option_args[0] + "'")
                sys.exit(1)
            else:
                raise

        if string.lower(non_option_args[1]) == "true" or \
           string.lower(non_option_args[1]) == "on" or \
           string.lower(non_option_args[1]) == "yes":
            value = ximian_xmlrpclib.True
        elif string.lower(non_option_args[1]) == "false" or \
             string.lower(non_option_args[1]) == "off" or \
             string.lower(non_option_args[1]) == "no":
            value = ximian_xmlrpclib.False
        else:
            try:
                value = int(non_option_args[1])
            except ValueError:
                value = non_option_args[1]

        success = 0
        try:
            server.rcd.prefs.set_pref(non_option_args[0], value)
            success = 1
        except ximian_xmlrpclib.Fault, f:
            if f.faultCode == rcfault.type_mismatch:
                # FIXME: This error message sucks
                rctalk.error("Can't set preference: " + f.faultString)
            elif f.faultCode == rcfault.cant_set_preference:
                rctalk.error(f.faultString)
            else:
                raise

        if success:
            rctalk.message("Preference '" + non_option_args[0] + "' changed from '" + str(pref) + "' to '" + str(value) + "'")

class PrefsListCmd(rccommand.RCCommand):

    def name(self):
        return "get-prefs"

    def aliases(self):
        return ["get", "prefs"]

    def arguments(self):
        return "<pref name> <pref name> ..."

    def description_short(self):
        return "List the system preferences that may be set"

    def category(self):
        return "prefs"

    def local_opt_table(self):
        return [["d", "no-descriptions", "", "Do not show descriptions of the preferences"]]

    def execute(self, server, options_dict, non_option_args):
        headers = ["Name", "Value"]
        pref_table = []
        
        if not non_option_args:
            if options_dict.has_key("no-descriptions"):
                f = lambda p:[p["name"], str(p["value"])]
            else:
                headers.append("Description")
                f = lambda p:[p["name"], str(p["value"]), p["description"]]

            pref_table = map(f, server.rcd.prefs.list_prefs())
        else:
            for a in non_option_args:
                try:
                    p = server.rcd.prefs.get_pref(a)
                except ximian_xmlrpclib.Fault, f:
                    if f.faultCode == rcfault.invalid_preference:
                        rctalk.warning("There is no preference named '" + a + "'")
                    else:
                        raise
                else:
                    pref_table.append([a, str(p)])

        pref_table.sort(lambda x,y:cmp(string.lower(x[0]),
                                       string.lower(y[0])))

        if pref_table:
            rcformat.tabular(headers, pref_table)

rccommand.register(PrefsListCmd)
rccommand.register(PrefsSetCmd)
            
