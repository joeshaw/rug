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
import rcformat
import rccommand
import rcchannelcmds

def get_packages(server, channel):
    return server.rcd.packsys.query([["channel","is",str(channel["id"])]])

def install_indicator(package):
    if (package["installed"]):
        return "i"
    else:
        return ""

class PackageListCmd(rccommand.RCCommand):

    def name(self):
        return "packages"

    def execute(self, server, options_dict, non_option_args):

        packages = [];
        package_table = [];

        for a in non_option_args:
            c = rcchannelcmds.get_channel_by_id(server, a)
            if not c:
                print "Invalid channel: '" + a + "'"
            else:
                packages = get_packages(server, c);

                map(lambda x,pt=package_table:pt.append([install_indicator(x), str(x["channel"]), x["name"], x["version"] + "-" + x["release"]]), packages)

        if package_table:
            package_table.sort(lambda x, y:cmp(x[2],y[2]))
            rcformat.tabular(["S", "Channel", "Name", "Version"], package_table)
        else:
            print "--- No packages found ---"

rccommand.register(PackageListCmd, "List the packages in a channel")
