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
import rcutil
import rctalk
import rcformat, rcchannelutils, rcchannelcmds
import rccommand
import rcfault
import ximian_xmlrpclib

class MountCmd(rccommand.RCCommand):

    def name(self):
        return "mount"

    def description_short(self):
        return "Mount a directory as a channel"

    def category(self):
        return "system"

    def arguments(self):
        return "<path>"

    def local_opt_table(self):
        return [["a", "alias", "alias", "Alias for new channel"],
                ["n", "name",  "channel name", "Name for new channel"]]

    def execute(self, server, options_dict, non_option_args):

        if len(non_option_args) == 0:
            # list mounted channels
            cmd = rcchannelcmds.ListChannelsCmd()
            cmd.execute(server, {"mounted": 1}, [])
            return

        path = os.path.abspath(non_option_args[0])
        path_base = os.path.basename(path)

        aliases = map(rcchannelutils.get_channel_alias,
                      rcchannelutils.get_channels(server))

        complain_about_collision = 0
        alias = string.lower(path_base)
        if options_dict.has_key("alias"):
            alias = options_dict["alias"]
            complain_about_collision = 1

        # Ensure we don't have an alias collision
        old_alias = alias
        count = 1
        while alias in aliases:
            alias = "%s%d" % (old_alias, count)
            count = count + 1
            
        if old_alias != alias and complain_about_collision:
            rctalk.warning("Alias '%s' already in use.  Using '%s' instead." %
                           (old_alias, alias))

        name = options_dict.get("name", path)
        try:
            success = server.rcd.packsys.mount_directory(path, name, alias)
        except ximian_xmlrpclib.Fault, f:
            if f.faultCode == rcfault.undefined_method:
                rctalk.error("Server does not support mount.")
                sys.exit(1)
            else:
                raise
        else:
            if success:
                rctalk.message("Mounted '%s' as a channel." % path)
            else:
                rctalk.error("Could not mount '%s' as a channel." % path)

class UnmountCmd(rccommand.RCCommand):

    def name(self):
        return "unmount"

    def description_short(self):
        return "Unmount a directory that has been mounted as a channel"

    def category(self):
        return "system"

    def arguments(self):
        return "<channel>"

    def execute(self, server, options_dict, non_option_args):

        if len(non_option_args) == 0:
            rctalk.error("No channel specified.")
            sys.exit(1)

        channel_name = non_option_args[0]
        channels = rcchannelutils.get_channels_by_name(server, channel_name)

        if not rcchannelutils.validate_channel_list(channel_name, channels):
            sys.exit(1)

        channel = channels[0]

        try:
            retval = server.rcd.packsys.unmount_directory(channel["id"])
        except ximian_xmlrpclib.Fault, f:
            if f.faultCode == rcfault.undefined_method:
                rctalk.error("Server does not support unmount.")
                sys.exit(1)
            else:
                raise
        else:
            if retval:
                rctalk.message("Unmounted channel '%s'" % channel["name"])
            else:
                rctalk.error("Unmount of channel '%s' failed" % channel["name"])

rccommand.register(MountCmd)
rccommand.register(UnmountCmd)
