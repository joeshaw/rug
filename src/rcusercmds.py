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

import os
import sys
import string
import rcutil
import rctalk
import rcformat
import rccommand

###
### "user-list" command

class UserListCmd(rccommand.RCCommand):

    def name(self):
        return "user-list"

    def is_hidden(self):
        return os.getuid() != 0

    def description_short(self):
        return "List users"

    def execute(self, server, options_dict, non_option_args):

        print server.rcd.users.get_all()

class UserUpdateCmd(rccommand.RCCommand):

    def name(self):
        return "user-update"

    def is_hidden(self):
        return os.getuid() != 0

    def description_short(self):
        return "Update users"

    def execute(self, server, options_dict, non_option_args):

        name, passwd, privileges = non_option_args

        passwd = rcutil.md5ify_password(passwd)
        server.rcd.users.update(name, passwd, privileges)


rccommand.register(UserListCmd)
rccommand.register(UserUpdateCmd)
