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

show_messages = 1
show_verbose  = 0
show_warnings = 1
show_errors   = 1
show_debug    = 0
be_terse      = 0

def message(str):
    if show_messages:
        print str

esc = "" 

def message_status(str):
    if show_messages and not be_terse:
        print esc + "[1G" + str + esc + "[0K",
        sys.stdout.flush()

def message_finished(str):
    if show_messages and not be_terse:
        print esc + "[1G" + str + esc + "[0K"

def verbose(str):
    if show_verbose:
        print str

def warning(str):
    if show_warnings:
        print "Warning: " + str

def error(str):
    if show_errors:
        print "ERROR: " + str

def fatal_error(str):
	if show_errors:
		print "ERRPR: " + str
		sys.exit(1)

def debug(str):
    if show_debug:
        print "DEBUG: " + str
    

