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

### XML-RPC faults that we care about back from the daemon.
###
### KEEP THIS IN SYNC WITH RCD!

type_mismatch          = -501 # matches xmlrpc-c
invalid_stream_type    = -503 # matches xmlrpc-c
undefined_method       = -506 # matches xmlrpc-c
permission_denied      = -600
package_not_found      = -601
package_is_newest      = -602
failed_dependencies    = -603
invalid_search_type    = -604
invalid_package_file   = -605
invalid_channel        = -606
invalid_transaction_id = -607
invalid_preference     = -608
locked                 = -609
cant_authenticate      = -610
cant_refresh           = -611
no_icon                = -612
cant_activate          = -613
