import string

command_dict = {}

def register(name, description, constructor):
    if command_dict.has_key(name):
        print "Command name collision: '"+name+"'"
    else:
        command_dict[name] = (description, constructor)

def construct(name):
    if command_dict.has_key(name):
        cons = (command_dict[name])[1]
        return cons()
    return None

def usage():
    print "Usage: rc <command> <options> ..."
    print
    print "Valid commands are:"
    keys = command_dict.keys()
    if keys:
        keys.sort()
        max_len = apply(max,map(len, keys))
        for k in keys:
            print "  " + string.ljust(k, max_len) + "  " + command_dict[k][0]
    else:
        print "<< No commands found --- something is wrong! >>"

class RCCommand:

    def opt_table(self):
        return [];

    def execute(self, server, options_dict, non_option_args):
        print "Execute not implemented!"
        sys.exit(1)


register("foo", "dummy command", RCCommand)
register("bar", "dummy command", RCCommand)

    
    
