
import string

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


###
### Code that actually does something.
###

def separated(table, separator):

    for r in table:
        print string.join(clean_row(r, separator), separator + " ")


def tabular(headers, table):

    def row_to_string(row, col_sizes):
        return string.join(pad_row(row, col_sizes), " | ")

    col_sizes = max_col_widths(table);

    if headers:
        col_sizes = map(max, map(len,headers), col_sizes)

        # print headers
        print string.join(pad_row(headers, col_sizes), " | ")

        # print head/body separator
        print string.join (map(lambda x:stutter("-",x), col_sizes), "-+-")

    # print table body
    for r in table:
        print row_to_string(r, col_sizes)

