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

import string
import re
import time
import rctalk
import rcchannelutils

###
### Utility functions.  Not really public.
###

def pad_row(row, col_sizes):
    return map(string.ljust, row, col_sizes)


def clean_row(row, separator):
    return map(lambda x, sep=separator:string.replace(x,sep,"_"), row)


def max_col_widths(table):
    return reduce(lambda v,w:map(max,v,w),
                  map(lambda x:map(len,x),table))


def stutter(str, N):
    if N <= 0:
        return ""
    return str + stutter(str, N-1)


def linebreak(in_str, width):

    str = string.strip(in_str)

    if not str:
        return []

    if len(str) <= width:
        return [str]
    
    if width < len(str) and str[width] == " ":
        n = width
    else:
        n = string.rfind(str[0:width], " ")

    lines = []
    
    if n == -1:
        lines.append(str)
    else:
        lines.append(str[0:n])
        lines = lines + linebreak(str[n+1:], width)

    return lines


## Assemble EVRs into strings

def evr_to_str(package):
    version = ""

    if package["has_epoch"]:
        version = version + str(package["epoch"]) + ":"

    version = version + package["version"]

    if package["release"]:
        version = version + "-" + package["release"]

    return version


## Assemble EVRs into abbreviated strings

def evr_to_abbrev_str(package):

    if string.find(package["release"], "snap") != -1:
        r = re.compile(".*(\d\d\d\d)(\d\d)(\d\d)(\d\d)(\d\d)")
        m = r.match(package["version"]) or r.match(package["release"])
        if m:
            return "%s-%s-%s, %s:%s" % \
                   (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))
        
    return evr_to_str(package)


## Assemble package specs/deps to strings

def rel_str(dep):
    rel = dep["relation"]
    if rel == "(any)":
        return ""
    else:
        return rel + " "

def dep_to_str(dep):
    return dep["name"] +  " " + rel_str(dep) + evr_to_str(dep)

def dep_to_abbrev_str(dep):
    return dep["name"] + " " + rel_str(dep) + evr_to_abbrev_str(dep)


## Shorten channel names in a semi-coherent way

def abbrev_channel_name(name):

    def abbrev(x):

        if string.find(x, "Snapshot") == 0:
            x = "Snaps"
        elif string.find(x, "Dev") == 0:
             x = "Dev"

        return x

    return string.join(filter(lambda x:x, map(abbrev, string.split(name))))


## Shorten importance strings

def abbrev_importance(str):
    return str[0:3]


## Extract data from a package

def package_to_row(server, pkg, no_abbrev, key_list):

    row = []

    for key in key_list:

        val = "?"

        if key == "installed":

            if pkg["installed"]:
                val = "i"
            else:
                val = ""

        elif key == "channel":

            if pkg.has_key("channel_guess"):
                id = pkg["channel_guess"]
            else:
                id = pkg["channel"]

            if id:
                val = rcchannelutils.channel_id_to_name(server, id)
            else:
                val = "unknown"

            if not no_abbrev:
                val = abbrev_channel_name(val)

        elif key == "version":

            if no_abbrev:
                val = evr_to_str(pkg)
            else:
                val = evr_to_abbrev_str(pkg)

        elif key == "name":

            # Trim long names
            val = pkg["name"]
            if not no_abbrev and len(val) > 25:
                val = val[0:22] + "..."

        elif pkg.has_key(key):
            val = pkg[key]

        row.append(val)

    return row
            


## Format quantities of seconds

def seconds_to_str(t):

    h = int(t/3600)
    m = int((t % 3600)/60)
    s = t % 60

    if h > 0:
        return "%dh%02dm%0ds" % (h, m, s)
        return "%ds" % t
    elif m > 0:
        return "%dm%02ds" % (m, s)
    else:
        return "%ds" % s


## Format quantities of bytes

def bytes_to_str(x):

    for fmt in ("%db", "%.2fk", "%.2fM", "%.2fg"):

        if x < 1024:
            return fmt % x

        x = x / 1024.0

    return "!!!"


## Format pending strings

def pending_to_str(p):

    pc = p["percent_complete"]
    msg = "%3d%%" % pc

    hash_max = 14
    hash_count = int(hash_max * pc / 100)
    hashes = "#" * hash_count + "-" * (hash_max - hash_count)

    msg = msg + " " + hashes

    if p.has_key("completed_size") and p.has_key("total_size"):
        cs = bytes_to_str(p["completed_size"])
        ts = bytes_to_str(p["total_size"])
        msg = msg + " (" + cs + "/" + ts + ")"

    status = p["status"]

    if status in ("pre_begin", "blocking", "running"):

        if p.has_key("elapsed_sec"):
            elap = p["elapsed_sec"]
            if elap >= 0:
                msg = msg + ", " + seconds_to_str(elap) + " elapsed"

                if p.has_key("remaining_sec"):
                    rem = p["remaining_sec"]
                    if rem >= 0:
                        msg = msg + ", " + seconds_to_str(rem) + " remaining"

                if elap > 0 and p.has_key("completed_size"):
                    rate = p["completed_size"] / elap
                    msg = msg + ", " + bytes_to_str(rate) + "/s"

    else:

        msg = msg + ", " + status
                        

    return msg


###
### Code that actually does something.
###

def separated(table, separator):

    for r in table:
        rctalk.message(string.join(clean_row(r, separator), separator + " "))


def aligned(table):

    col_sizes = max_col_widths(table)

    for r in table:
        rctalk.message(string.join(pad_row(r, col_sizes), " "))


def opt_table(table):

    opt_list = []

    for r in table:
        opt = "--" + r[1]
        if r[0]:
            opt = "-" + r[0] + ", " + opt
        if r[2]:
            opt = opt + "=<" + r[2] + ">"

        opt_list.append([opt + "  ", r[3]])

    # By appending [0,0], we insure that this will work even if
    # opt_list is empty (which it never should be)
    max_len = apply(max, map(lambda x:len(x[0]), opt_list) + [0,0])

    for opt, desc_str in opt_list:

        if 79 - max_len > 10:
            desc = linebreak(desc_str, 79 - max_len)
        else:
            desc = [desc_str]

        desc_first = desc.pop(0)
        rctalk.message(string.ljust(opt, max_len) + desc_first)
        for d in desc:
            rctalk.message(" " * max_len + d)


def tabular(headers, table):

    def row_to_string(row, col_sizes):
        if rctalk.be_terse:
            return string.join(row, "|")
        else:
            return string.join(pad_row(row, col_sizes), " | ")

    col_sizes = max_col_widths(table)

    if headers and not rctalk.be_terse:
        col_sizes = map(max, map(len,headers), col_sizes)

        # print headers
        rctalk.message(string.join(pad_row(headers, col_sizes), " | "))

        # print head/body separator
        rctalk.message(string.join (map(lambda x:stutter("-",x), col_sizes), "-+-"))

    # print table body
    for r in table:
        rctalk.message(row_to_string(r, col_sizes))

###
### Format transaction status messages into readable text
###

def transaction_status(message):
    messages = {"download"  : "Downloading Packages",
                "verify"    : "Verifying",
                "prepare"   : "Preparing Transaction",
                "install"   : "Installing",
                "remove"    : "Removing",
                "configure" : "Configuring",
                "finish"    : "Transaction finished",
                "failed"    : "Transaction failed:"}

    status = string.split(message, ":", 0)

    m = messages[status[0]]
    if len(status) > 1:
        return m + " " + string.join(status[1:], ":")
    else:
        return m
