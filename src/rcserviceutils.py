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

import string
import ximian_xmlrpclib

cached_services = None

def get_services(server):
    global cached_services
    
    if cached_services is not None:
        return cached_services

    cached_services = server.rcd.service.list()

    return cached_services

def find_service(services, match):

    match = string.lower(match)

    index = 1
    for s in services:
        # Can't mess with invisible services.
        if s["is_invisible"]:
            continue

        if str(index) == match:
            return s

        for sub in ("id", "url", "name"):
            if string.lower(s[sub]) == match:
                return s

        index = index + 1

