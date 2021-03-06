###
### Copyright 2003 Ximian, Inc.
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

import rcchannelutils
import rccommand
import rcfault
import rcformat
import rcserviceutils
import rctalk
import ximian_xmlrpclib

class ServiceListCmd(rccommand.RCCommand):

    def name(self):
        return "service-list"

    def aliases(self):
        return ["sl"]

    def description_short(self):
        return "List the current services"

    def category(self):
        return "service"

    def local_opt_table(self):
        return [["", "show-ids", "", "Show service IDs"]]

    def execute(self, server, options_dict, non_option_args):

        if options_dict.has_key("show-ids"):
            show_ids = 1
        else:
            show_ids = 0

        services = rcserviceutils.get_services(server)

        if options_dict.has_key("verbose"):
            self.verbose_output(server, services)
        else:
            self.columned_output(server, services, show_ids)

    def columned_output(self, server, services, show_ids=0):
        table = []
        row_no = 1

        for serv in services:
            if serv.has_key("is_invisible") and serv["is_invisible"]:
                continue

            if serv.has_key("name"):
                name = serv["name"]
            else:
                name = "(No name available)"

            if show_ids:
                row = [str(row_no), serv["id"], serv["url"], name]
            else:
                row = [str(row_no), serv["url"], name]
                
            table.append(row)

            row_no = row_no + 1

        if table:
            if show_ids:
                headers = ["#", "Service ID", "Service URI", "Name"]
            else:
                headers = ["#", "Service URI", "Name"]

            rcformat.tabular(headers, table)
        else:
            rctalk.message("*** No services are mounted ***")

    def verbose_output(self, server, services):
        for serv in services:
            if serv.has_key("is_invisible") and serv["is_invisible"]:
                continue

            rctalk.message("       Service ID: %s" % serv["id"])
            rctalk.message("     Service Name: %s" % serv["name"])
            rctalk.message("      Service URI: %s" % serv["url"])

            if serv.has_key("distro_name"):
                rctalk.message("Distribution type: %s %s (%s)" %
                               (serv["distro_name"], serv["distro_version"],
                                serv["distro_target"]))

            if serv.has_key("contact_email"):
                rctalk.message("    Contact email: %s" % serv["contact_email"])

            if serv.has_key("premium_service"):
                rctalk.message("  RCX/RCE Service: %s" %
                               ((serv["premium_service"] and "yes") or "no"))
                
            rctalk.message("")

class ServiceAddCmd(rccommand.RCCommand):

    def name(self):
        return "service-add"

    def aliases(self):
        return ["sa"]

    def arguments(self):
        return "<service uri> ..."

    def description_short(self):
        return "Add a new service."

    def category(self):
        return "service"

    def execute(self, server, options_dict, non_option_args):
        if len(non_option_args) < 1:
            self.usage()
            sys.exit(1)

        services = rcserviceutils.get_services(server)

        for o in non_option_args:
            for s in services:
                if string.lower(s["url"]) == o:
                    rctalk.error("Service '%s' already exists" % s["name"])
                    sys.exit(1)
            
            try:
                server.rcd.service.add(o)
            except ximian_xmlrpclib.Fault, f:
                rctalk.error(f.faultString)
                sys.exit(1)
            else:
                rctalk.message("Service '%s' successfully added." % o)


class ServiceDeleteCmd(rccommand.RCCommand):

    def name(self):
        return "service-delete"

    def aliases(self):
        return ["sd"]

    def arguments(self):
        return "<service> ..."

    def description_short(self):
        return "Delete a service. Specify service URI, name, or number."

    def category(self):
        return "service"

    def execute(self, server, options_dict, non_option_args):
        if len(non_option_args) < 1:
            self.usage()
            sys.exit(1)

        services = rcserviceutils.get_services(server)

        for o in non_option_args:
            s = rcserviceutils.find_service(services, o)

            if not s:
                rctalk.error("No service matches '%s'" % o)
                sys.exit(1)
            
            try:
                server.rcd.service.remove(s["id"])
            except ximian_xmlrpclib.Fault, f:
                if f.faultCode != rcfault.invalid_service:
                    raise

                rctalk.error(f.faultString)
            else:
                rctalk.message("Service '%s' successfully removed." % s["name"])


class ServiceMirrorsCmd(rccommand.RCCommand):

    def name(self):
        return "mirrors"

    def aliases(self):
        return []

    def arguments(self):
        return "<service> <mirror #>"

    def description_short(self):
        return "Select a mirror for a service"

    def category(self):
        return "service"

    def local_opt_table(self):
        return [["l", "list-only", "", "List the available mirrors"]]

    def execute(self, server, options_dict, non_option_args):

        if len(non_option_args) < 1 or len(non_option_args) > 2:
            self.usage()
            sys.exit(1)

        services = rcserviceutils.get_services(server)
        service = rcserviceutils.find_service(services, non_option_args[0])

        if not service:
            rctalk.error("No service matches '%s'" % non_option_args[0])
            sys.exit(1)

        verbose = options_dict.has_key("verbose")
        list_only = options_dict.has_key("list-only")

        select_str = ""

        show_list = 1
        allow_select = not list_only

        if len(non_option_args) > 1:
            show_list = 0
            allow_select = 0
            select_str = non_option_args[1]

        current_host = service["url"]

        def sort_cb(a, b):
            aname = string.lower(a["name"])
            bname = string.lower(b["name"])

            # "All Animals Are Equal / But Some Are More Equal Than Others."
            if aname[:6] == "ximian":
                aname = "a" * 10
            if bname[:6] == "ximian":
                bname = "a" * 10
                
            return cmp(aname, bname)

        try:
            mirrors = server.rcd.service.get_mirrors(service["id"])
        except ximian_xmlrpclib.Fault, f:
            if f.faultCode == rcfault.invalid_service:
                mirrors = None

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
            try:
                server.rcd.service.set_url(service["id"], choice["url"])
            except ximian_xmlrpclib.Fault, f:
                if f.faultCode == rcfault.invalid_service:
                    rctalk.error(f.faultString)
                else:
                    raise

class ServiceRefreshCmd(rccommand.RCCommand):

    def name(self):
        return "refresh"

    def aliases(self):
        return ["ref"]

    def category(self):
        return "system"

    def arguments(self):
        return "<service>"

    def description_short(self):
        return "Refresh channel data"

    def execute(self, server, options_dict, non_option_args):

        if len(non_option_args) > 1:
            self.usage()
            sys.exit(1)

        if non_option_args:
            services = rcserviceutils.get_services(server)
            s = rcserviceutils.find_service(services, non_option_args[0])

            if not s:
                rctalk.error("No service matches '%s'" % non_option_args[0])
                sys.exit(1)
                
            rcchannelutils.refresh_channels(server, s["id"])
        else:
            rcchannelutils.refresh_channels(server)

class ServiceActivateCmd(rccommand.RCCommand):

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
        return [["s", "service", "service", "Activate against \"service\""],
                ["a", "alias", "alias", "Use \"alias\" to name this machine"],
                ["n", "no-refresh", "", "Don't refresh channel data after a successful activation"]]

    def execute(self, server, options_dict, non_option_args):
        if len(non_option_args) < 2:
            self.usage()
            sys.exit(1)

        err_str = None
        success = 0

        activation_info = {}
        activation_info["activation_code"] = non_option_args[0]
        activation_info["email"] = non_option_args[1]

        if options_dict.has_key("service"):
            services = rcserviceutils.get_services(server)
            s = rcserviceutils.find_service(services, options_dict["service"])

            if not s:
                rctalk.error("No service matches '%s'" %
                             options_dict["service"])
                sys.exit(1)
            
            activation_info["service"] = s["id"]

        if options_dict.has_key("alias"):
            activation_info["alias"] = options_dict["alias"]

        try:
            server.rcd.service.activate(activation_info)
        except ximian_xmlrpclib.Fault, f:
            if f.faultCode == rcfault.cant_activate \
                   or f.faultCode == rcfault.invalid_service:
                
                err_str = f.faultString
                success = 0
            else:
                raise
        else:
            success = 1

        if success:
            rctalk.message("System successfully activated")

            if not options_dict.has_key("no-refresh"):
                rcchannelutils.refresh_channels(server)
            
        else:
            if not err_str:
                err_str = "Invalid activation code or email address"
            
            rctalk.warning("System could not be activated: %s" % err_str)
            sys.exit(1)

rccommand.register(ServiceListCmd)
rccommand.register(ServiceAddCmd)
rccommand.register(ServiceDeleteCmd)
rccommand.register(ServiceMirrorsCmd)
rccommand.register(ServiceRefreshCmd)
rccommand.register(ServiceActivateCmd)
