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

class PrefsMirrorsCmd(rccommand.RCCommand):

    def name(self):
        return "mirrors"

    def aliases(self):
        return []

    def arguments(self):
        return "<mirror #>"

    def description_short(self):
        return "Select a mirror"

    def category(self):
        return "prefs"

    def local_opt_table(self):
        return [["l", "list-only", "", "List the available mirrors"]]

    def execute(self, server, options_dict, non_option_args):

        verbose = options_dict.has_key("verbose")
        list_only = options_dict.has_key("list-only")

        select_str = ""

        show_list = 1
        allow_select = not list_only

        if non_option_args:
            show_list = 0
            allow_select = 0
            select_str = non_option_args[0]

        current_host = server.rcd.prefs.get_pref("host")

        def sort_cb(a, b):
            aname = string.lower(a["name"])
            bname = string.lower(b["name"])

            # "All Animals Are Equal / But Some Are More Equal Than Others."
            if aname[:6] == "ximian":
                aname = "a" * 10
            if bname[:6] == "ximian":
                bname = "a" * 10
                
            return cmp(aname, bname)

        mirrors = server.rcd.mirror.get_all()

        if not mirrors:
            rctalk.message("--- No mirrors available ---")
            return
        
        mirrors.sort(sort_cb)

        if show_list:
            table = []
            i = 1
            for m in mirrors:
                short_name = m["name"]
                if len(short_name) > 35 and not verbose:
                    short_name = short_name[:32] + "..."
                    
                num = str(i)
                if m["url"] == current_host:
                    num = "*" + num
                else:
                    num = " " + num
                
                table.append([num, short_name, m.get("location", "Unknown")])
                if verbose:
                    table.append(["", m["url"]])
                i = i + 1

            rcformat.tabular([" #", "Mirror", "Location"], table)

        if allow_select:
            rctalk.message("")
            rctalk.message("To select a mirror, type the mirror's number at")
            rctalk.message("at the prompt and press return.")
            rctalk.message("")

            print "Mirror: ",
            select_str = string.strip(sys.stdin.readline())
            rctalk.message("")
            if not select_str:
                rctalk.message("No mirror selected.")
                return

        if not select_str:
            return
            
        n = -1
        try:
            n = int(select_str)
        except:
            pass

        if not (1 <= n <= len(mirrors)):
            rctalk.error("'%s' is not a valid mirror." % select_str)
            sys.exit(1)

        choice = mirrors[n-1]

        sel_table = []
        sel_table.append(["Name", choice["name"]])
        sel_table.append(["Location", choice.get("location", "Unknown")])
        sel_table.append(["URL", choice["url"]])

        key_width = apply(max, map(lambda x: len(x[0]), sel_table))

        rctalk.message("Selected Mirror:")
        for key, val in sel_table:
            key = " " * (key_width - len(key)) + key
            rctalk.message("%s: %s" % (key, val))

        if choice["url"] != current_host:
            rctalk.message("")
            server.rcd.prefs.set_pref("host", choice["url"])
            rcchannelutils.refresh_channels(server, [])
        
                      

rccommand.register(PrefsListCmd)
rccommand.register(PrefsSetCmd)
rccommand.register(PrefsMirrorsCmd)
            
