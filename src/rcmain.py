#!/usr/bin/python

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

rc_name = "Red Carpet Command Line Client"
rc_copyright = "Copyright (C) 2000-2003 Ximian Inc.  All Rights Reserved."
rc_version = None

# Whether we are connecting over Unix domain sockets or TCP.
local = 0

def import_commands(rug_dir):
    import glob, imp
    sysdir = rug_dir + "/commands"
    sys.path.append(sysdir)

    loaded_modules = []

    # First load modules in our current directory, for developers, and then
    # out of the system dir.
    files = glob.glob("*cmds.py")
    files = files + glob.glob("%s/*cmds.py" % sysdir)
    
    for file in files:
        (path, name) = os.path.split(file)
        (name, ext) = os.path.splitext(name)
        
        if name in loaded_modules:
            continue
        
        (file, filename, data) = imp.find_module(name, [path])

        try:
            module = imp.load_module(name, file, filename, data)
        except ImportError:
            rctalk.warning("Can't import module " + filename)
        else:
            loaded_modules.append(name)

        if file:
            file.close()

def main(ver, rug_dir):

    global local
    global rc_version

    rc_version = ver

    if os.environ.has_key("RC_DEBUG"):
        rctalk.show_debug = 1

    import_commands(rug_dir)

    ###
    ### Grab the option list and extract the first non-option argument that
    ### looks like a command.  This could get weird if someone passes the name
    ### of a command as the argument to an option.
    ###

    argv = sys.argv[1:]

    argv = rccommand.expand_synthetic_args(argv)

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

    # A hack to suppress extra whitespace when dumping.
    if command.name() == "dump":
        rctalk.be_terse = 1

    argv = rccommand.get_user_default_args(argv, command)

    opt_dict, args = command.process_argv(argv)


    ###
    ### Open a connection to the server.
    ###

    # If the hostname has a / in it, we assume that it is actually
    # an explicitly-specified to a socket.
    if command.name() == "help":
        local = 1 # A hack so that you don't need to type your password
                  # when asking for help
    elif opt_dict.has_key("host") and string.find(opt_dict["host"], "/") == 0:
        local = 1
    elif opt_dict.has_key("host") or opt_dict.has_key("user"):
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

        # Prepend "https://" if it isn't already specified
        if string.find(host, "http://") == -1 \
               and string.find(host, "https://") == -1:
            host = "https://" + host

        # Append the port number (505) if one isn't specified
        hparts = string.split(host, ":", 2)
        if len(hparts) < 3:
            hparts.append("505")
        url = string.join(hparts, ":") + "/RPC2"

        if (opt_dict.has_key("user")):
            username = opt_dict["user"]
        else:
            username = getpass.getuser()
        

        if (opt_dict.has_key("password")):
            password = rcutil.md5ify_password(opt_dict["password"])
        else:
            password = rcutil.md5ify_password(getpass.getpass())

    else:
        if opt_dict.has_key("host"):
            url = opt_dict["host"]
        else:
            url = "/var/run/rcd/rcd"

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

    if opt_dict.has_key("quiet"):
        rctalk.show_messages = 0
        rctalk.show_warnings = 0

    if opt_dict.has_key("verbose"):
        rctalk.show_verbose = 1

    ### Whitespace is nice, so we always print a blank line before
    ### executing the command

    if not rctalk.be_terse:
        rctalk.message("")

    ###
    ### Execute the command
    ###

    try:
        command.execute(server, opt_dict, args)
    except IOError:
        # Just quietly exit in this case, too.  It is probably a
        # broken pipe from something like quitting "less" before
        # rc is finished.
        print
        sys.exit(0)
    except socket.error, e:
        rctalk.error("Unable to connect to the daemon: " + str(e))
        rctalk.error("Please ensure that the service is running.")
        sys.exit(1)
    except ximian_xmlrpclib.ProtocolError, e:
        if e.errcode == -1:
            rctalk.error("Unable to connect to the daemon.  Please check ")
            rctalk.error("the hostname and protocol.")
            sys.exit(1)
        elif e.errcode == 401:
            rctalk.error("Unable to authenticate your username and/or password")
            sys.exit(1)
        else:
            raise
    except ximian_xmlrpclib.Fault, f:
        if f.faultCode == rcfault.cant_authenticate:
            rctalk.error("Unable to authenticate your username and/or password")
        elif f.faultCode == rcfault.permission_denied:
            rctalk.error("You do not have permissions to perform the requested action.")
        else:
            raise
        sys.exit(1)
    except NotImplementedError:
        rctalk.error("This system's python is built without SSL support.  SSL is required for remote connections")
        sys.exit(1)
    except vars(socket).has_key("sslerror") and socket.sslerror, e:
        rctalk.error("Unable to make a secure connection to the daemon: " + str(e))
        sys.exit(1)

    ### Whitespace is nice, so we always print a blank line after
    ### executing the command

    if not rctalk.be_terse:
        rctalk.message("")

