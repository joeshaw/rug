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
import os
import string
import getopt

# For exception handling.
import socket
import cgiwrap

import ximian_xmlrpclib
import rctalk
import rccommand
import rcsystemcmds
import rcchannelcmds
import rcpackagecmds
import rclogcmds
import rcnewscmds

rc_name = "Red Carpet Command Line Client"
rc_copyright = "Copyright (C) 2000-2002 Ximian Inc.  All Rights Reserved."

def main(rc_version):

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

    command = None
    found_name = 0
    i = 0
    while i < len(argv) and not command:
        if argv[i][0] != "-":
            found_name = 1
            command = rccommand.construct(argv[i])
            if command:
                argv.pop(i)
        else:
            takes_arg = 0
            for o in rccommand.default_opt_table:
                if not (argv[i][1:] == o[0] or argv[i][2:] == o[1]):
                    continue

                if o[2] != "":
                    takes_arg = 1
                    break

            if takes_arg and string.find(argv[i], "=") == -1:
                i = i + 1

        i = i + 1

    if not found_name:
        rctalk.warning("No command found on command line.")
        rccommand.usage()
        sys.exit(1)

    if not command:
        rccommand.usage()
        sys.exit(1)

    if "-?" in argv or "--help" in argv:
        command.usage()
        sys.exit(0)

    ###
    ### Handle .rcrc, RC_ARGS, --read-from-file and --read-from-stdin
    ###

    # We add arguments to the beginning of argv.  This means we can
    # override an magically added arg by explicitly putting the
    # orthogonal arg on the command line.
    def join_args(arglist, argv):
        return map(string.strip, arglist) + argv


    # Try to read the .rcrc file.  It basically works like a .cvsrc file.
    if "--ignore-rc-file" not in argv:
        try:
            rcrc = open(os.path.expanduser("~/.rcrc"), "r")
            while 1:
                line = rcrc.readline()

                # strip out comments
                hash_pos = string.find(line, "#")
                if hash_pos >= 0:
                    line = line[0:hash_pos]

                # skip empty lines
                if not line:
                    break
                
                pieces = string.split(line)
                if len(pieces) and pieces[0] == command.name():
                    argv = join_args(pieces[1:], argv)
            rcrc.close()
            
        except IOError:
            # If we can't open the .rcrc file, that is fine... just
            # continue as if nothing happened.
            pass
        

    if "--ignore-env" not in argv and os.environ.has_key("RC_ARGS"):
        args = string.split(os.environ["RC_ARGS"])
        argv = join_args(args, argv)

    # FIXME: Should support --read-from-file=foo.txt syntax!
    if "--read-from-file" in argv:
        i = argv.index("--read-from-file") + 1
        if i < len(argv):
            filename = argv[i]
            lines = []
            try:
                f = open(filename, "r")
                lines = f.readlines()
            except IOError:
                rctalk.error("Couldn't open file '" + filename + "'")
                sys.exit(1)
            argv = join_args(lines, argv)
        else:
            rctalk.error("No filename provided for --read-from-file option")
            sys.exit(1)

    if "--read-from-stdin" in argv:
        lines = sys.stdin.readlines()
        argv = join_args(lines, argv)

    ###
    ### Find the list of command line options associated with the command.
    ### Then compile our list of arguments into something that getopt can
    ### understand.  Finally, call getopt on argv
    ###

    opt_table = command.opt_table()

    short_opt_getopt = ""
    long_opt_getopt  = []

    short2long_dict = {}

    for o in opt_table:

        short_opt = o[0]
        long_opt  = o[1]
        opt_desc  = o[2]

        if short_opt:

            if short2long_dict.has_key(short_opt):
                rctalk.error("Short option collision!")
                rctalk.error("-" + short_opt + ", --" + long_opt)
                rctalk.error("  vs.")
                rctalk.error("-" + short_opt + ", --" + short2long_dict[short_opt])
                sys.exit(1)

            short2long_dict[short_opt] = long_opt
            short_opt_getopt = short_opt_getopt + short_opt
            if opt_desc:
                short_opt_getopt = short_opt_getopt + ":"

        if opt_desc:
            long_opt_getopt.append(long_opt + "=")
        else:
            long_opt_getopt.append(long_opt)


    try:
        optlist, args = getopt.getopt(argv, short_opt_getopt, long_opt_getopt)
    except getopt.error:
        rctalk.error("Unrecognized arguments")
        command.usage()
        sys.exit(1)

    ###
    ### Walk through our list of options and replace short options with the
    ### corresponding long option.
    ###
    
    i = 0
    while i < len(optlist):
        key = optlist[i][0]
        if key[0:2] != "--":
            optlist[i][0] = opt_dict[short2long_dict[key[1:]]]
        i = i + 1


    ###
    ### Get the list of "orthogonal" options for this command and, if our
    ### list of options contains orthogonal elements, remove all but the
    ### last such option.
    ### (i.e. if we are handed --quiet --verbose, we drop the --quiet)
    ### 

    optlist.reverse()
    for oo_list in command.orthogonal_opts():
        i = 0
        seen_oo = 0
        while i < len(optlist):
            key = optlist[i][0]
            if key[2:] in oo_list:
                if seen_oo:
                    del optlist[i]
                    i = i - 1
                seen_oo = 1
            i = i + 1
    optlist.reverse()


    ###
    ### Store our options in a dictionary
    ###

    opt_dict = {}

    for key, value in optlist:
            opt_dict[key[2:]] = value


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

        url = "http://" + host + "/RPC2"

        if (opt_dict.has_key("user")):
            username = opt_dict["user"]

        if (opt_dict.has_key("password")):
            password = opt_dict["password"]
    else:
        url = "/tmp/rcd"

    try:
        server = ximian_xmlrpclib.Server(url,
                                         auth_username=username,
                                         auth_password=password)
    except:
        rctalk.error("Unable to connect to the daemon.")
        sys.exit(1)

    # FIXME: check for error here.  Maybe we should ping the server
    # before going further?

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
    except socket.error:
        rctalk.error("Unable to connect to the daemon.")
        rctalk.error("Please ensure that the service is running.")
        sys.exit(1)
    except cgiwrap.ProtocolError, e:
        if e.errcode == 401:
            rctalk.error("Unable to authenticate with the daemon.")
        else:
            raise
    except ximian_xmlrpclib.Fault, f:
        if f.faultCode == -610:
            rctalk.error("You do not have permissions to perform the requested action.")
        else:
            raise
