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

import os
import sys
import string
import re
import getpass
import rcutil
import rctalk
import rcformat
import rccommand
import rcfault
import ximian_xmlrpclib


def get_password(msg="Password"):
    p1, p2 = "foo", "bar"

    while p1 != p2:

        try:
            p1 = getpass.getpass("%s: " % msg)
        except KeyboardInterrupt:
            p1 = ""
                
        if not p1:
            return ""

        try:
            p2 = getpass.getpass("Confirm %s: " % msg)
        except KeyboardInterrupt:
            p2 = ""
                
        if not p2:
            return ""
                
        if p1 != p2:
            rctalk.message("Passwords do not match.  Please try again.")

    rctalk.message("Passwords match.")

    return rcutil.md5ify_password(p1)


def get_privileges(initial, in_legal):

    legal = in_legal
    legal.sort()
    legal.append("superuser")

    current = {}
    for priv in initial:
        if string.lower(priv) in legal:
            current[string.lower(priv)] = 1

    rctalk.message("")
    rctalk.message("At the prompt, type +/- followed by a privilege name to add/remove")
    rctalk.message("that privilege.  To accept the current set of privileges, press return.")

    while 1:
        table = []
        for l in legal:
            if current.has_key("superuser") or current.has_key(l):
                flag = "yes"
            else:
                flag = "no"

            table.append([l, flag])

        rctalk.message("")
        rctalk.message("Current Privileges:")
        rcformat.aligned(table)

        print "Changes: ",
        changes = string.split(sys.stdin.readline())

        if not changes:
            return current.keys()

        # Yuck.  Handle spaces between "+"/"-" and priv name
        max = len(changes)
        filter = []
        i = 0
        while i < max:
            # If "+" or "-" is by itself and not the last thing on the line
            if changes[i] in ("+", "-") and i+1 < max:
                filter.append(changes[i] + changes[i+1])
                i++
            else:
                filter.append(changes[i])

            i++

        changes = filter
        
        for change in changes:
            x = string.lower(change)
            valid = 0
            if len(x) > 1:
                pm = x[0]
                priv = x[1:]

                if pm in ["+", "-"] and priv in legal:
                    if pm == "+":
                        current[priv] = 1
                        valid = 1
                    elif pm == "-":
                        if current.has_key(priv):
                            del current[priv]
                        valid = 1

            if not valid:
                rctalk.warning("Ignoring invalid privilege setting \"" + change + "\"")
            
    

###
### "user-list" command
###

class UserListCmd(rccommand.RCCommand):

    def name(self):
        return "user-list"

    def aliases(self):
        return ["ul"]

    def description_short(self):
        return "List users"

    def category(self):
        return "user"

    def execute(self, server, options_dict, non_option_args):
        users = server.rcd.users.get_all()
        if users:
            rcformat.tabular(["Username", "Privileges"], users)
        else:
            rctalk.message("--- No users found ---")


###
### "user-add" command
###

class UserAddCmd(rccommand.RCCommand):

    def name(self):
        return "user-add"

    def aliases(self):
        return ["ua"]

    def arguments(self):
        return "<UserName> <Privilege> <Privilege> ..."

    def description_short(self):
        return "Add a new user"

    def category(self):
        return "user"

    def execute(self, server, options_dict, non_option_args):

        users = map(lambda x:x[0], server.rcd.users.get_all())
        valid_privs = map(string.lower, server.rcd.users.get_valid_privileges())
        
        privs = []
        if non_option_args:
            for p in non_option_args[1:]:
                if p and string.lower(p) in valid_privs:
                    privs.append(string.lower(p))
                else:
                    rctalk.warning("Ignoring unrecognized privilege '"+p+"'")

        if non_option_args:
            username = non_option_args[0]
        else:
            print "Username: ",

            try:
                username = string.strip(sys.stdin.readline())
            except KeyboardInterrupt:
                username = ""
                
            if not username:
                rctalk.message("Exiting")
                sys.exit(0)
                
            if not re.compile("^\w+$").match(username):
                rctalk.error("Invalid user name")
                sys.exit(1)

        if username in users:
            rctalk.error("User '" + username + "' already exists.")
            sys.exit(1)

        passwd = get_password()
        if not passwd:
            rctalk.message("Exiting.")
            sys.exit(0)

        if not privs and "view" in valid_privs:
            privs = ["view"]

        privs = get_privileges(privs, valid_privs)
        privs_str = string.join(privs, ", ")

        rc = server.rcd.users.update(username, passwd, privs_str)

        rctalk.message("")

        if rc:
            rctalk.message("User '" + username + "' added.")
        else:
            rctalk.error("User '" + username + "' could not be added.")

###
### "user-delete" command
###

class UserDeleteCmd(rccommand.RCCommand):

    def name(self):
        return "user-delete"

    def aliases(self):
        return ["ud"]

    def arguments(self):
        return "<username> <username> ..."

    def description_short(self):
        return "Delete users"

    def category(self):
        return "user"
    
    def local_opt_table(self):
        return [["s", "strict", "", "Fail if attempting to delete a non-existent user"]]

    def execute(self, server, options_dict, non_option_args):

        if options_dict.has_key("strict"):
            all_users = map(lambda x:x[0], server.rcd.users.get_all())
            failed = 0
            for username in non_option_args:
                if not username in all_users:
                    rctalk.warning("User '" + username + "' does not exist")
                    failed = 1
            if failed:
                rctalk.error("User deletion cancelled")
        
        for username in non_option_args:
            if not server.rcd.users.remove(username):
                rctalk.warning("Attempt to delete user '" + username + "' failed")
            else:
                rctalk.message("User '" + username + "' deleted.")


class UserEditCmd(rccommand.RCCommand):

    def name(self):
        return "user-edit"

    def aliases(self):
        return ["ue"]

    def arguments(self):
        return "<username>"

    def description_short(self):
        return "Edit an existing user"

    def category(self):
        return "user"

    def local_opt_table(self):
        return [["p", "change-password", "", "Change the user's password"]]

    def execute(self, server, options_dict, non_option_args):

        if not non_option_args:
            rctalk.error("No user specified.")
            sys.exit(1)

        username = non_option_args[0]
        # Damn you, python 1.5.x.  I want my lexical closures!
        matching = filter(lambda x,y=username:x[0] == y,
                          server.rcd.users.get_all())

        if not matching:
            rctalk.error("Unknown user '%s'" % username)
            sys.exit(1)

        new_password = "-*-unchanged-*-"
        if options_dict.has_key("change-password"):
            new_password = get_password("New Password")

        set_privs = 1
        try:
            set_privs = server.rcd.users.has_privilege("superuser")
        except ximian_xmlrpclib.Fault, f:
            # If our daemon doesn't have has_privilege, just let them
            # try.
            if f.faultCode != rcfault.undefined_method:
                raise

        if set_privs:
            user = matching[0]
            current_privs = string.split(user[1], ", ")

            valid_privs = map(string.lower,
                              server.rcd.users.get_valid_privileges())
            new_privs = get_privileges(current_privs, valid_privs)
            new_privs_str = string.join(new_privs, ", ")
        else:
            new_privs_str = "-*-unchanged-*-"

        if not set_privs and not options_dict.has_key("change-password"):
            # Lame.  Fake a permission denied fault so the user gets the
            # stock "no permissions error"
            raise ximian_xmlrpclib.Fault(rcfault.permission_denied,
                                         "Permission denied")

        rctalk.message("")
        
        if server.rcd.users.update(username, new_password, new_privs_str):
            rctalk.message("Saved changes to user '%s'" % username)
        else:
            rctalk.warning("Couldn't save changes to user '%s'" % username)


rccommand.register(UserListCmd)
rccommand.register(UserAddCmd)
rccommand.register(UserDeleteCmd)
rccommand.register(UserEditCmd)

