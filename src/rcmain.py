#!/usr/bin/python

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
import string
import getpass
import os

# For exception handling.
import socket

import ximian_xmlrpclib
import rcutil
import rctalk
import rccommand
import rcfault
import rcsystemcmds
import rcchannelcmds
import rcpackagecmds
import rcusercmds
import rcwhatcmds
import rclogcmds
import rcnewscmds
import rcprefscmds

rc_name = "Red Carpet Command Line Client"
rc_copyright = "Copyright (C) 2000-2002 Ximian Inc.  All Rights Reserved."

# Whether we are connecting over Unix domain sockets or TCP.
local = 0

def main(rc_version):

    global local

    ###
    ### Grab the option list and extract the first non-option argument that
    ### looks like a command.  This could get weird if someone passes the name
    ### of a command as the argument to an option.
    ###

    argv = sys.argv[1:]

    if "--version" in argv:
        print
        print rc_name + " " + rc_version
        print rc_copyright
        print
        sys.exit(0)

    command = rccommand.extract_command_from_argv(argv)

    if "-?" in argv or "--help" in argv:
        command.usage()
        sys.exit(0)


    opt_dict, args = command.process_argv(argv)


    ###
    ### Open a connection to the server.
    ###

    if opt_dict.has_key("host") or opt_dict.has_key("user"):
        local = 0
    else:
        local = 1

    username = None
    password = None

    if not local:
        if opt_dict.has_key("host"):
            host = opt_dict["host"]
        else:
            host = "localhost"

        if string.find(host, ":") == -1:
            host = host + ":5505"

        url = "https://" + host + "/RPC2"

        if (opt_dict.has_key("user")):
            username = opt_dict["user"]

        if (opt_dict.has_key("password")):
            password = rcutil.md5ify_password(opt_dict["password"])
        else:
            password = rcutil.md5ify_password(getpass.getpass())

    else:
        url = "/tmp/rcd"

    if os.environ.has_key("RC_TRANSPORT_DEBUG"):
        transport_debug = 1
    else:
        transport_debug = 0

    try:
        server = ximian_xmlrpclib.Server(url,
                                         auth_username=username,
                                         auth_password=password,
                                         verbose=transport_debug)
    except:
        rctalk.error("Unable to connect to the daemon.")
        sys.exit(1)

    ###
    ### Control verbosity
    ###

    if opt_dict.has_key("terse"):
        rctalk.be_terse = 1

    if opt_dict.has_key("debug"):
        rctalk.show_debug = 1

    if opt_dict.has_key("quiet"):
        rctalk.show_messages = 0
        rctalk.show_warnings = 0

    if opt_dict.has_key("verbose"):
        rctalk.show_verbose = 1

    ###
    ### Execute the command
    ###

    try:
        command.execute(server, opt_dict, args)
    except socket.error, e:
        rctalk.error("Unable to connect to the daemon: " + str(e))
        rctalk.error("Please ensure that the service is running.")
        sys.exit(1)
    except ximian_xmlrpclib.ProtocolError, e:
        if e.errcode == 401:
            rctalk.error("Unable to authenticate with the daemon; you must")
            rctalk.error("provide a username and password")
        else:
            raise
    except ximian_xmlrpclib.Fault, f:
        if f.faultCode == rcfault.cant_authenticate:
            rctalk.error("Unable to authenticate your username and/or password")
        elif f.faultCode == rcfault.permission_denied:
            rctalk.error("You do not have permissions to perform the requested action.")
        else:
            raise
