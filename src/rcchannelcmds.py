import rcformat
import rccommand

cached_channel_list = []

def get_channels(server):
    global cached_channel_list
    if not cached_channel_list:
        cached_channel_list = server.rcd.packsys.get_channels()
    return cached_channel_list

def get_channel_by_id(server, id):
    channels = get_channels(server)
    for c in channels:
        if str(c["id"]) == str(id):
            return c

def channel_id_to_name(server, id):
    channels = get_channels(server)
    for c in channels:
        if str(c["id"]) == str(id):
            return c["name"]

class ListChannelsCmd(rccommand.RCCommand):

    def execute(self, server, options_dict, non_option_args):

        channels = get_channels(server)
        channel_table = []

        for c in channels:

            if c["subscribed"]:
                subflag = " Yes "
            else:
                subflag = ""
                
            channel_table.append([subflag, str(c["id"]), c["name"]])

            channel_table.sort(lambda x, y:cmp(x[2],y[2]))

        rcformat.tabular(["subd?", "ID", "Name"], channel_table)


class SubscribeCmd(rccommand.RCCommand):

    def execute(self, server, options_dict, non_option_args):

        for a in non_option_args:
            if not get_channel_by_id(server, a):
                print "Invalid channel id: " + a
                sys.exit(1)

        for a in non_option_args:
            c = get_channel_by_id(server, a)
            if c and server.rcd.packsys.subscribe(int(a)):
                print "Subscribed to channel '"+c["name"]+"' (ID# "+str(c["id"])+")"


class UnsubscribeCmd(rccommand.RCCommand):

    def execute(self, server, options_dict, non_option_args):

        for a in non_option_args:
            if not get_channel_by_id(server, a):
                print "Invalid channel id: " + a
                sys.exit(1)

        for a in non_option_args:
            c = get_channel_by_id(server, a)
            if c and server.rcd.packsys.unsubscribe(int(a)):
                print "Unsubscribed to channel '"+c["name"]+"' (ID# "+str(c["id"])+")"





rccommand.register("channels", "List available channels", ListChannelsCmd)
rccommand.register("subscribe", "Subscribe to a channel", SubscribeCmd)
rccommand.register("unsubscribe", "Unsubscribe from a channel", UnsubscribeCmd)
