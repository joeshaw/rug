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

import re
import string
import sys
import time

import rcmain
import rctalk
import rcfault
import rcformat
import rccommand
import rcchannelutils
import rcpackageutils
import ximian_xmlrpclib

###
### Transacting commands 
###

DRY_RUN       = 1
DOWNLOAD_ONLY = 2

def extract_package(dep_or_package):
    # Check to see if we're dealing with package op structures or real
    # package structures.  Package structures won't have a "package" key.

    if dep_or_package.has_key("package"):
        return dep_or_package["package"]
    else:
        return dep_or_package

def extract_packages(dep_or_package_list):
    return map(lambda x:extract_package(x), dep_or_package_list)

def format_dependencies(server, dep_list):
    dep_list.sort(lambda x,y:cmp(string.lower(extract_package(x)["name"]),
                                 string.lower(extract_package(y)["name"])))

    dlist = []
    for d in dep_list:
        p = extract_package(d)

        c = rcchannelutils.channel_id_to_name(server, p["channel"])
        if c:
            c = "(" + c + ")"
        else:
            c = ""

        rctalk.message("  " + p["name"] + " " + rcformat.evr_to_str(p) +
                       " " + c)

        if d.has_key("details"):
            map(lambda x:rctalk.message("    " + x), d["details"])

    rctalk.message("")

def filter_dups(list):
    for l in list:
        count = list.count(l)
        if count > 1:
            for i in range(1, count):
                list.remove(l)

    return list

def verify_dependencies(server):
    try:
        return server.rcd.packsys.verify_dependencies()
    except ximian_xmlrpclib.Fault, f:
        if f.faultCode == rcfault.failed_dependencies:
            rctalk.error(f.faultString)
            sys.exit(1)
        else:
            raise

def resolve_dependencies(server, install_packages,
                         remove_packages, extra_reqs):
    install_packages = filter_dups(install_packages)
    remove_packages = filter_dups(remove_packages)
    extra_reqs = filter_dups(extra_reqs)

    try:
        return server.rcd.packsys.resolve_dependencies (install_packages,
                                                        remove_packages,
                                                        extra_reqs)
    except ximian_xmlrpclib.Fault, f:
        if f.faultCode == rcfault.failed_dependencies:
            rctalk.error(f.faultString)
            sys.exit(1)
        else:
            raise

###
### Base class for all transaction-based commands
###

class TransactCmd(rccommand.RCCommand):
    def unattended_removals(self):
        return 0
    
    def local_opt_table(self):
        opts = [["N", "dry-run", "", "Do not actually perform requested actions"],
                ["y", "no-confirmation", "", "Permit all actions without confirmations"]]

        if not self.unattended_removals():
            opts.append(["r", "allow-removals", "", "Permit removal of software without confirmation"])

        return opts

    def display(self, server, options_dict,
                install_packages, install_deps,
                remove_packages, remove_deps):

        if options_dict.has_key("download-only"):
            rctalk.message("The following packages will be downloaded:")
            format_dependencies(server, install_packages)
        else:
            if install_packages:
                rctalk.message("The following requested packages will "
                               "be installed:")
                format_dependencies(server, install_packages)

            if install_deps:
                if install_packages:
                    rctalk.message("The following additional packages will "
                                   "be installed:")
                else:
                    rctalk.message("The following packages will be installed:")

                format_dependencies(server, install_deps)

            if remove_packages:
                rctalk.message("The following requested packages will "
                               "be removed:")
                format_dependencies(server, remove_packages)

            if remove_deps:
                if remove_packages:
                    rctalk.message("The following packages must also "
                                   "be REMOVED:")
                else:
                    rctalk.message("The following packages must be REMOVED")

                format_dependencies(server, remove_deps)

            if not options_dict.has_key("terse"):
                msg_list = []
                count = len(install_packages) + len(install_deps)

                if count:
                    msg_list.append("%d packages will be installed" % count)

                count = len(remove_packages) + len(remove_deps)
                if count:
                    msg_list.append("%d packages will be removed" % count)

                rctalk.message("%s." % string.join(msg_list, " and "))

        if not options_dict.has_key("terse"):
            # Of course, this will be inaccurate if packages are already
            # in the cache.  We try to do something reasonable if a
            # file size is missing.
            total_size = 0
            approximate = 0
            for p in install_packages:
                p = extract_package(p)
                sz = p.get("file_size", 0)
                total_size = total_size + sz
                if sz == 0:
                    approximate = 1
            for p in install_deps:
                p = extract_package(p)
                sz = p.get("file_size", 0)
                total_size = total_size + sz
                if sz == 0:
                    approximate = 1

            if total_size > 0:
                size_str = rcformat.bytes_to_str(total_size)
                approx_str = ""
                if approximate:
                    approx_str = "at least "
                rctalk.message("This is %sa %s download." % (approx_str,
                                                             size_str))

    def confirm(self, options_dict, removals):
        if not options_dict.has_key("no-confirmation"):
            confirm = rctalk.prompt("Do you want to continue? [y/N]")
            if not confirm or not (confirm[0] == "y" or confirm[0] == "Y"):
                rctalk.message("Cancelled.")
                sys.exit(0)

        allow_remove = self.unattended_removals() \
                       or options_dict.has_key("allow-removals")

        if removals \
           and options_dict.has_key("no-confirmation") \
           and not allow_remove:
            rctalk.warning("Removals are required.  Use the -r option or "
                           "confirm interactively.")
            sys.exit(1)            
        
    def check_licenses(self, server, packages):
        try:
            licenses = server.rcd.license.lookup_from_packages(packages)
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
                        rctalk.message_finished("Transaction failed: %s" % pending["error_msg"])
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

    def transact(self, server, options_dict,
                 install_packages, install_deps,
                 remove_packages, remove_deps):
        
        self.display(server, options_dict,
                     install_packages, install_deps,
                     remove_packages, remove_deps)

        if not options_dict.has_key("download-only"):
            self.confirm(options_dict, remove_packages + remove_deps)

        # FIXME: Skipping over if no-confirmation is set is wrong.
        if not options_dict.has_key("no-confirmation"):
            self.check_licenses(server,
                                install_packages + extract_packages(install_deps))

        if options_dict.has_key("dry-run"):
            flags = DRY_RUN
        elif options_dict.has_key("download-only"):
            flags = DOWNLOAD_ONLY
        else:
            flags = 0

        download_id, transact_id, step_id = \
                     server.rcd.packsys.transact(install_packages + extract_packages(install_deps),
                                                 remove_packages + extract_packages(remove_deps),
                                                 flags,
                                                 rcmain.rc_name,
                                                 rcmain.rc_version)

        self.poll_transaction(server, download_id, transact_id, step_id)


###
### "install" command
###

class PackageInstallCmd(TransactCmd):

    def name(self):
        return "install"

    def is_basic(self):
        return 1

    def aliases(self):
        return ["in"]

    def category(self):
        return "package"

    def arguments(self):
        return "<package-name> <package-name> ..."

    def description_short(self):
        return "Install packages"

    def local_opt_table(self):
        opts = TransactCmd.local_opt_table(self)

        opts.append(["u", "allow-unsubscribed", "", "Include unsubscribed channels when searching for software"])
        opts.append(["d", "download-only", "", "Only download packages, don't install them"])
        opts.append(["", "entire-channel", "", "Install all of the packages in the channels specified on the command line"])

        return opts

    def execute(self, server, options_dict, non_option_args):
        packages_to_install = []
        packages_to_remove = []
        
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
                         ["package-installed", "=", "false"]]
                packages = server.rcd.packsys.search(query)
                packages_to_install.extend(packages)
                if len(packages) > 0:
                    contributors = contributors + 1
                msg = "Found %d %s in channel '%s'" % \
                      (len(packages),
                       (len(packages) != 1 and "packages") or "package",
                       c["name"])
                rctalk.message(msg)

            if contributors > 1:
                msg = "Found a total of %d %s" % \
                      (len(packages_to_install),
                       (len(packages_to_install) != 1 and "packages")
                       or "package")
                rctalk.message(msg)

            rctalk.message("")

        else:
            
            for a in non_option_args:
                inform = 0
                channel = None
                package = None

                if a[0] == "!" or a[0] == "~":
                    pn = a[1:]
                    plist = rcpackageutils.find_package_on_system(server, pn)

                    if not plist:
                        rctalk.error("Unable to find package '" + pn + "'")
                        sys.exit(1)

                    for p in plist:
                        packages_to_remove.append(p)
                else:
                    plist = rcpackageutils.find_package(server, a,
                                                        allow_unsub,
                                                        allow_system=0)

                    if not plist:
                        sys.exit(1)

                    for p in plist:
                        dups = filter(lambda x, pn=p:x["name"] == pn["name"],
                                      packages_to_install)

                        if dups:
                            rctalk.error("Duplicate entry found: " +
                                         dups[0]["name"])
                            sys.exit(1)

                        packages_to_install.append(p)

        if not packages_to_install and not packages_to_remove:
            rctalk.message("--- No packages to install ---")
            sys.exit(0)

        install_deps, remove_deps, dep_info = \
                      resolve_dependencies(server,
                                           packages_to_install,
                                           packages_to_remove,
                                           [])

        self.transact(server, options_dict,
                      packages_to_install, install_deps,
                      packages_to_remove, remove_deps)

###
### "remove" command
###

class PackageRemoveCmd(TransactCmd):
    def name(self):
        return "remove"

    def is_basic(self):
        return 1

    def category(self):
        return "package"

    def aliases(self):
        return ["re", "rm", "erase"]

    def arguments(self):
        return "<package-name> <package-name> ..."

    def description_short(self):
        return "Remove packages"

    def unattended_removals(self):
        return 1

    def execute(self, server, options_dict, non_option_args):
        packages_to_remove = []
        
        for a in non_option_args:
            plist = rcpackageutils.find_package_on_system(server, a)

            if not plist:
                rctalk.error("Unable to find package '" + a + "'")
                sys.exit(1)

            for p in plist:
                dups = filter(lambda x, pn=p:x["name"] == pn["name"],
                              packages_to_remove)

                if dups:
                    rctalk.warning("Duplicate entry found: " + dups[0]["name"])
                else:
                    packages_to_remove.append(p)

        if not packages_to_remove:
            rctalk.message("--- No packages to remove ---")
            sys.exit(0)

        install_deps, remove_deps, dep_info = \
                      resolve_dependencies(server,
                                           [],
                                           packages_to_remove,
                                           [])

        self.transact(server, options_dict,
                      [], [],
                      packages_to_remove, remove_deps)

###
### "update" command
###

class PackageUpdateCmd(TransactCmd):

    def name(self):
        return "update"

    def is_basic(self):
        return 1

    def category(self):
        return "package"

    def aliases(self):
        return ["up"]

    def arguments(self):
        return "<channel> <channel> ..."

    def description_short(self):
        return "Download and install available updates"

    def local_opt_table(self):
        opts = TransactCmd.local_opt_table(self)

        opts.append(["i", "importance", "importance", "Only install updates as or more important than 'importance' (valid are " + str(rcpackageutils.update_importances.keys()) + ")"])
        opts.append(["d", "download-only", "", "Only download packages, don't install them"])

        return opts

    def execute(self, server, options_dict, non_option_args):
        min_importance = None
        if options_dict.has_key("importance"):
            if not rcpackageutils.update_importances.has_key(options_dict["importance"]):
                rctalk.error("Invalid importance: " +
                             options_dict["importance"])
                sys.exit(1)
            else:
                min_importance = rcpackageutils.update_importances[options_dict["importance"]]
        
        update_list = rcpackageutils.get_updates(server, non_option_args)

        if min_importance != None:
            up = []
            for u in update_list:
                # higher priorities have lower numbers... i know, i know...
                if u[1]["importance_num"] <= min_importance:
                    up.append(u)
        else:
            up = update_list

        # x[1] is the package to be updated
        packages_to_install = map(lambda x:x[1], up)

        if not packages_to_install:
            rctalk.message("--- No packages to update ---")
            sys.exit(0)

        install_deps, remove_deps, dep_info = \
                      resolve_dependencies(server,
                                           packages_to_install,
                                           [],
                                           [])

        self.transact(server, options_dict,
                      packages_to_install, install_deps,
                      [], remove_deps)

###
### "verify" command
###

class PackageVerifyCmd(TransactCmd):

    def name(self):
        return "verify"

    def aliases(self):
        return ["ve"]

    def category(self):
        return "package"

    def arguments(self):
        return ""

    def description_short(self):
        return "Verify system dependencies"

    def execute(self, server, options_dict, non_option_args):
        install_deps, remove_deps, dep_info =  verify_dependencies(server)

        if not install_deps and not remove_deps:
            rctalk.message("System dependency tree verified successfully.")
            sys.exit(0)
        
        self.transact(server, options_dict,
                      [], install_deps,
                      [], remove_deps)

def date_converter(date_str):
    try:
        time.gmtime(int(date_str))
    except (ValueError, TypeError):
        # Not a valid time_t
        pass
    else:
        return int(date_str)
    
    # Ugh.  This sucks.
    formats_to_try = (
        "%x",                      # locale-specific date representation
        "%X",                      # locale-specific time representation
        "%x %X",                   # locale-specific date, then time.
        "%X %x",                   # locale-specific time, then date.
        "%a %b %d %H:%M:%S %Y",    # Thu May 29 13:28:47 2003
        "%a %b %d %H:%M:%S %Z %Y", # Thu May 29 13:28:47 EDT 2003
        "%d %b %Y",                # 29 May 2003
        "%d %b %Y %H:%M:%S",       # 29 May 2003 13:28:47
        "%d %b %Y %H:%M:%S %Z",    # 29 May 2003 13:28:47 EDT
        "%y-%m-%d",                # 03-05-29
        "%Y-%m-%d",                # 2003-05-29
        "%y-%m-%d %H:%M:%S",       # 03-05-29 13:28:47
        "%Y-%m-%d %H:%M:%S",       # 2003-05-29 13:28:47
        "%H:%M:%S",                # 13:28:47
        "%H:%M",                   # 13:28
        "%I:%M:%S %p",             # 1:28:47 PM
        "%I:%M %p",                # 1:28 PM
    )

    date = None
    for format in formats_to_try:
        try:
            date = time.strptime(date_str, format)
        except ValueError:
            # no dice.
            continue
        else:
            # disco.
            break

    if date:
        return time.mktime(date)
        
    time_dict = {
        "second" : 1,
        "minute" : 60,
        "hour"   : 3600,
        "day"    : 86400,
        "week"   : 604800,
        "month"  : 2592000, # FIXME: 30 days, inexact
        "year"   : 31536000 # FIXME: 365 days, inexact
    }

    date_str = string.lower(date_str)

    if string.find(date_str, "ago") != -1:
        r = re.compile("^(\d+)(?:\s+)(.+)(?:\s+)(?:ago)$")
        match = r.match(date_str)

        if not match:
            raise ValueError, "Unknown date '%s'" % date_str

        val = int(match.group(1))
        time_spec = match.group(2)
        if time_dict.has_key(time_spec):
            mult = time_dict[time_spec]
        elif time_dict.has_key(time_spec[:-1]):
            mult = time_dict[time_spec[:-1]]
        else:
            raise ValueError, "Unknown unit of time '%s'" % time_spec

        return time.time() - (val * mult)
    elif string.find(date_str, "last") != -1:
        r = re.compile("^(?:last)(?:\s+)(.+)$")
        match = r.match(date_str)

        if not match:
            raise ValueError, "Unknown date '%s'" % date_str

        time_spec = match.group(1)
        if not time_dict.has_key(time_spec):
            raise ValueError, "Unknown unit of time '%s'" % time_spec

        return time.time() - time_dict[time_spec]
    elif string.find(date_str, "yesterday") != -1:
        return time.time() - time_dict["day"]
    else:
        raise ValueError, "Unknown date '%s'" % date_str

class PackageRollbackCmd(TransactCmd):

    def name(self):
        return "rollback"

    def aliases(self):
        return ["ro"]

    def category(self):
        return "package"

    def arguments(self):
        return "<time>"

    def description_short(self):
        return "Rollback transactions to a specified time"

    def local_opt_table(self):
        opts = TransactCmd.local_opt_table(self)

        opts.append(["d", "download-only", "", "Only download packages, don't install them"])

        return opts

    def execute(self, server, options_dict, non_option_args):
        if len(non_option_args) < 1:
            self.usage()
            sys.exit(1)

        try:
            when = int(date_converter(string.join(non_option_args, " ")))
        except ValueError, e:
            rctalk.error("Unable to rollback: %s" % e)
            return 1

        install_packages, remove_packages = \
                          server.rcd.packsys.get_rollback_actions(when)

        if not install_packages and not remove_packages:
            rctalk.message("--- Nothing to rollback ---")
            return

        self.display(server, options_dict,
                     install_packages, [],
                     remove_packages, [])

        self.confirm(options_dict, remove_packages)

        if options_dict.has_key("dry-run"):
            flags = DRY_RUN
        elif options_dict.has_key("download-only"):
            flags = DOWNLOAD_ONLY
        else:
            flags = 0

        download_id, transact_id, step_id = \
                     server.rcd.packsys.rollback(when, flags,
                                                 rcmain.rc_name,
                                                 rcmain.rc_version)

        self.poll_transaction(server, download_id, transact_id, step_id)

###
### "solvedeps" command
###

class PackageSolveCmd(TransactCmd):

    def name(self):
        return "solvedeps"

    def aliases(self):
        return ["sd", "solve"]

    def arguments(self):
        return "<package-dep>"

    def description_short(self):
        return "Resolve dependencies for libraries"

    def category(self):
        return "dependency"

    def execute(self, server, options_dict, non_option_args):
        if options_dict.has_key("dry-run"):
            dry_run = 1
        else:
            dry_run = 0

        dlist = []

        for d in non_option_args:
            dep = {}
            package = string.split(d)

            if len(package) > 1:
                valid_relations = ["=", "<", "<=", ">", ">=", "!="]

                if not package[1] in valid_relations:
                    rctalk.error("Invalid relation.")
                    sys.exit(1)

                dep["name"] = package[0]
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
                dep["name"] = d
                dep["relation"] = "(any)"
                dep["has_epoch"] = 0
                dep["epoch"] = 0
                dep["version"] = "*"
                dep["release"] = "*"

            dups = filter(lambda x, d=dep:x["name"] == d["name"], dlist)

            if dups:
                rctalk.warning("Duplicate entry found: " + dups[0]["name"])

            dlist.append(dep)

        install_deps, remove_deps, dep_info = \
                      resolve_dependencies(server, [], [], dlist)

        if not install_deps and not remove_deps:
            rctalk.message("Requirements are already met on the system.  No "
                           "packages need to be")
            rctalk.message("installed or removed.")
            sys.exit(0)

        self.transact(server, options_dict,
                      [], install_deps,
                      [], remove_deps)

rccommand.register(PackageInstallCmd)
rccommand.register(PackageRemoveCmd)
rccommand.register(PackageUpdateCmd)
rccommand.register(PackageVerifyCmd)
rccommand.register(PackageSolveCmd)
rccommand.register(PackageRollbackCmd)
