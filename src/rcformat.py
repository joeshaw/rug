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
import rctalk

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


###
### Code that actually does something.
###

def separated(table, separator):

    for r in table:
        print string.join(clean_row(r, separator), separator + " ")


def aligned(table):

    col_sizes = max_col_widths(table)

    for r in table:
        print string.join(pad_row(r, col_sizes), " ")


def opt_table(table):

    opt_list = []

    for r in table:
        opt = "--" + r[1]
        if r[0]:
            opt = "-" + r[0] + ", " + opt
        if r[2]:
            opt = opt + "=<" + r[2] + ">"

        opt_list.append([opt + "  ", r[3]])

    aligned(opt_list)
    


def tabular(headers, table):

    def row_to_string(row, col_sizes):
        if rctalk.be_terse:
            return string.join(row, "|")
        else:
            return string.join(pad_row(row, col_sizes), " | ")

    col_sizes = max_col_widths(table);

    if headers and not rctalk.be_terse:
        col_sizes = map(max, map(len,headers), col_sizes)

        # print headers
        print string.join(pad_row(headers, col_sizes), " | ")

        # print head/body separator
        print string.join (map(lambda x:stutter("-",x), col_sizes), "-+-")

    # print table body
    for r in table:
        print row_to_string(r, col_sizes)

###
### Code for displaying versions of packages
###
def display_version(package):
    version = ""
    
    if package["epoch"]:
        version = version + str(package["epoch"]) + ":"

    version = version + package["version"]

    if package["release"]:
        version = version + "-" + package["release"]

    return version

        
