#
# XML-RPC CLIENT LIBRARY
# $Id$
#
# an XML-RPC client interface for Python.
#
# the marshalling and response parser code can also be used to
# implement XML-RPC servers.
#
# Copyright (c) 1999 by Secret Labs AB.
# Copyright (c) 1999 by Fredrik Lundh.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# Copyright (C) 2000, 2001 Red Hat, Inc.
#   * Cristian Gafton <gafton@redhat.com>:
#       - Add cgiwrap as a CGI wrapper that allows for
#         automatically compressing/decompressing of data before
#         sending it on the wire
#       - Added https support with the ability of checking the
#         remote site SSL certificate agains a known list of CAs.
#   * Preston Brown <pbrown@redhat.com>
#       - Add proxy support
#
# Copyright (C) 2002 Ximian, Inc.
#   * Joe Shaw <joe@ximian.com:
#       - Add HTTP Basic auth for non-proxies
#       - Work over Unix domain sockets by specifying a file instead of
#         a URL to the constructor

import string
import time
import urllib, xmllib
import base64
import httplib
import socket
from types import *
from cgi import escape
# For portability
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


try:
    import sgmlop
except ImportError:
    sgmlop = None # accelerator not available

__version__ = "$Revision$"


# --------------------------------------------------------------------
# Exceptions

class Error:
    # base class for client errors
    pass


class ProtocolError(Error):
    # indicates an HTTP protocol error
    def __init__(self, url, errcode, errmsg, headers):
	self.url = url
	self.errcode = errcode
	self.errmsg = errmsg
	self.headers = headers
    def __repr__(self):
	return (
	    "<ProtocolError for %s: %s %s>" %
	    (self.url, self.errcode, self.errmsg)
	    )


class ResponseError(Error):
    # indicates a broken response package
    pass


class Fault(Error):
    # indicates a XML-RPC fault package
    def __init__(self, faultCode, faultString, **extra):
	self.faultCode = faultCode
	self.faultString = faultString
    def __repr__(self):
        return "<Fault %s \"\"\"%s\"\"\">" % (self.faultCode, self.faultString)
    __str__ = __repr__

# --------------------------------------------------------------------
# Special values


#
# boolean wrapper
# (you must use True or False to generate a "boolean" XML-RPC value)
class Boolean:

    def __init__(self, value = 0):
	self.value = (value != 0)

    def encode(self, out):
	out.write("<value><boolean>%d</boolean></value>\n" % self.value)

    def __repr__(self):
	if self.value:
	    return "<Boolean True at %x>" % id(self)
	else:
	    return "<Boolean False at %x>" % id(self)

    def __int__(self):
	return self.value

    def __nonzero__(self):
	return self.value

True, False = Boolean(1), Boolean(0)


#
# dateTime wrapper
# (wrap your iso8601 string or time tuple or localtime time value in
# this class to generate a "dateTime.iso8601" XML-RPC value)
class DateTime:

    def __init__(self, value = 0):
	t = type(value)
	if t is not StringType:
	    if t is not TupleType:
		value = time.localtime(value)
	    value = time.strftime("%Y%m%dT%H:%M:%S", value)
	self.value = value

    def __repr__(self):
	return "<DateTime %s at %x>" % (self.value, id(self))

    def decode(self, data):
	self.value = string.strip(data)

    def encode(self, out):
	out.write("<value><dateTime.iso8601>")
	out.write(self.value)
	out.write("</dateTime.iso8601></value>\n")

#
# binary data wrapper (NOTE: this is an extension to Userland's
# XML-RPC protocol! only for use with compatible servers!)
class Binary:

    def __init__(self, data=None):
	self.data = data

    def decode(self, data):
	self.data = base64.decodestring(data)

    def encode(self, out):

	out.write("<value><base64>\n")
	base64.encode(StringIO(self.data), out)
	out.write("</base64></value>\n")


class File:
    def __init__(self, file_obj, length = 0, name = None):
        self.length = length
        self.file_obj = file_obj
        self.read = file_obj.read
        self.close = file_obj.close
        self.name = ""
        if name:
            self.name = name[string.rfind(name, "/")+1:]
    def __len__(self):
        return self.length

WRAPPERS = DateTime, Binary, Boolean




# --------------------------------------------------------------------
# XML parsers

if sgmlop:

    class FastParser:
	# sgmlop based XML parser.  this is typically 15x faster
	# than SlowParser...

	def __init__(self, target):

	    # setup callbacks
	    self.finish_starttag = target.start
	    self.finish_endtag = target.end
	    self.handle_data = target.data

	    # activate parser
	    self.parser = sgmlop.XMLParser()
	    self.parser.register(self)
	    self.feed = self.parser.feed
	    self.entity = {
		"amp": "&", "gt": ">", "lt": "<",
		"apos": "'", "quot": '"'
		}

	def close(self):
	    try:
		self.parser.close()
	    finally:
		self.parser = self.feed = None # nuke circular reference

	def handle_entityref(self, entity):
	    # <string> entity
	    try:
		self.handle_data(self.entity[entity])
	    except KeyError:
		self.handle_data("&%s;" % entity)

else:

    FastParser = None


class SlowParser(xmllib.XMLParser):
    # slow but safe standard parser, based on the XML parser in
    # Python's standard library

    def __init__(self, target):
	self.unknown_starttag = target.start
	self.handle_data = target.data
	self.unknown_endtag = target.end
	xmllib.XMLParser.__init__(self)




# --------------------------------------------------------------------
# XML-RPC marshalling and unmarshalling code

class Marshaller:
    """Generate an XML-RPC params chunk from a Python data structure"""

    # USAGE: create a marshaller instance for each set of parameters,
    # and use "dumps" to convert your data (represented as a tuple) to
    # a XML-RPC params chunk.  to write a fault response, pass a Fault
    # instance instead.  you may prefer to use the "dumps" convenience
    # function for this purpose (see below).

    # by the way, if you don't understand what's going on in here,
    # that's perfectly ok.

    def __init__(self):
	self.memo = {}
	self.data = None

    dispatch = {}

    def dumps(self, values):
	self.__out = []
	self.write = write = self.__out.append
	if isinstance(values, Fault):
	    # fault instance
	    write("<fault>\n")
	    self.__dump(vars(values))
	    write("</fault>\n")
	else:
	    # parameter block
	    write("<params>\n")
	    for v in values:
		write("<param>\n")
		self.__dump(v)
		write("</param>\n")
	    write("</params>\n")
	result = string.join(self.__out, "")
	del self.__out, self.write # don't need this any more
	return result

    def __dump(self, value):
	try:
	    f = self.dispatch[type(value)]
	except KeyError:
	    raise TypeError, "cannot marshal %s objects" % type(value)
	else:
	    f(self, value)

    def dump_int(self, value):
	self.write("<value><int>%s</int></value>\n" % value)
    dispatch[IntType] = dump_int

    def dump_double(self, value):
	self.write("<value><double>%s</double></value>\n" % value)
    dispatch[FloatType] = dump_double

    def dump_string(self, value):
	self.write("<value><string>%s</string></value>\n" % escape(value))
    dispatch[StringType] = dump_string

    def container(self, value):
	if value:
	    i = id(value)
	    if self.memo.has_key(i):
		raise TypeError, "cannot marshal recursive data structures"
	    self.memo[i] = None
    
    def endcontainer(self, value):
        if value:
            del self.memo[id(value)]

    def dump_array(self, value):
	self.container(value)
	write = self.write
	write("<value><array><data>\n")
	for v in value:
	    self.__dump(v)
	write("</data></array></value>\n")
        self.endcontainer(value)
    dispatch[TupleType] = dump_array
    dispatch[ListType] = dump_array

    def dump_struct(self, value):
	self.container(value)
	write = self.write
	write("<value><struct>\n")
	for k, v in value.items():
	    write("<member>\n")
	    if type(k) is not StringType:
		raise TypeError, "dictionary key must be string"
	    write("<name>%s</name>\n" % escape(k))
	    self.__dump(v)
	    write("</member>\n")
	write("</struct></value>\n")
        self.endcontainer(value)
    dispatch[DictType] = dump_struct

    def dump_instance(self, value):
	# check for special wrappers
	if value.__class__ in WRAPPERS:
	    value.encode(self)
	else:
            if hasattr(value, "__getstate__"):
                self.__dump(getattr(value, "__getstate__")())
            else:
                # store instance attributes as a struct (really?)
                self.dump_struct(value.__dict__)
    dispatch[InstanceType] = dump_instance


class Unmarshaller:

    # unmarshal an XML-RPC response, based on incoming XML event
    # messages (start, data, end).  call close to get the resulting
    # data structure

    # note that this reader is fairly tolerant, and gladly accepts
    # bogus XML-RPC data without complaining (but not bogus XML).

    # and again, if you don't understand what's going on in here,
    # that's perfectly ok.

    def __init__(self):
	self._type = None
	self._stack = []
        self._marks = []
	self._data = []
	self._methodname = None
	self.append = self._stack.append

    def close(self):
	# return response code and the actual response
	if self._type is None or self._marks:
	    raise ResponseError()
	if self._type == "fault":
	    raise apply(Fault, (), self._stack[0])
	return tuple(self._stack)

    def getmethodname(self):
	return self._methodname

    #
    # event handlers

    def start(self, tag, attrs):
	# prepare to handle this element
	if tag in ("array", "struct"):
	    self._marks.append(len(self._stack))
	self._data = []
	self._value = (tag == "value")

    def data(self, text):
	self._data.append(text)

    dispatch = {}

    def end(self, tag):
	# call the appropriate end tag handler
	try:
	    f = self.dispatch[tag]
	except KeyError:
	    pass # unknown tag ?
	else:
	    return f(self)

    #
    # element decoders

    def end_boolean(self, join=string.join):
	value = join(self._data, "")
	if value == "0":
	    self.append(False)
	elif value == "1":
	    self.append(True)
	else:
	    raise TypeError, "bad boolean value"
	self._value = 0
    dispatch["boolean"] = end_boolean

    def end_int(self, join=string.join):
        # I hope this catches out of bound values
        try:
            self.append(int(join(self._data, "")))
        except ValueError:
            self.append(str(join(self._data, "")))
	self._value = 0
    dispatch["i4"] = end_int
    dispatch["int"] = end_int

    def end_double(self, join=string.join):
	self.append(float(join(self._data, "")))
	self._value = 0
    dispatch["double"] = end_double

    def end_string(self, join=string.join):
	self.append(join(self._data, ""))
	self._value = 0
    dispatch["string"] = end_string
    dispatch["name"] = end_string # struct keys are always strings

    def end_array(self):
        mark = self._marks[-1]
	del self._marks[-1]
	# map arrays to Python lists
        self._stack[mark:] = [self._stack[mark:]]
	self._value = 0
    dispatch["array"] = end_array

    def end_struct(self):
        mark = self._marks[-1]
	del self._marks[-1]
	# map structs to Python dictionaries
        dict = {}
        items = self._stack[mark:]
        for i in range(0, len(items), 2):
            dict[items[i]] = items[i+1]
        self._stack[mark:] = [dict]
	self._value = 0
    dispatch["struct"] = end_struct

    def end_base64(self, join=string.join):
	value = Binary()
	value.decode(join(self._data, ""))
	self.append(value)
	self._value = 0
    dispatch["base64"] = end_base64

    def end_dateTime(self, join=string.join):
	value = DateTime()
	value.decode(join(self._data, ""))
	self.append(value)
    dispatch["dateTime.iso8601"] = end_dateTime

    def end_value(self):
	# if we stumble upon an value element with no internal
	# elements, treat it as a string element
	if self._value:
	    self.end_string()
    dispatch["value"] = end_value

    def end_params(self):
	self._type = "params"
    dispatch["params"] = end_params

    def end_fault(self):
	self._type = "fault"
    dispatch["fault"] = end_fault

    def end_methodName(self, join=string.join):
	self._methodname = join(self._data, "")
    dispatch["methodName"] = end_methodName




# --------------------------------------------------------------------
# convenience functions

def getparser():
    # get the fastest available parser, and attach it to an
    # unmarshalling object.  return both objects.
    target = Unmarshaller()
    if FastParser:
	return FastParser(target), target
    return SlowParser(target), target


def dumps(params, methodname=None, methodresponse=None):
    # convert a tuple or a fault object to an XML-RPC packet

    assert type(params) == TupleType or isinstance(params, Fault),\
	   "argument must be tuple or Fault instance"

    m = Marshaller()
    data = m.dumps(params)

    # standard XML-RPC wrappings
    if methodname:
	# a method call
	data = (
	    "<?xml version='1.0'?>\n"
	    "<methodCall>\n"
	    "<methodName>%s</methodName>\n"
	    "%s\n"
	    "</methodCall>\n" % (methodname, data)
	    )
    elif methodresponse or isinstance(params, Fault):
	# a method response
	data = (
	    "<?xml version='1.0'?>\n"
	    "<methodResponse>\n"
	    "%s\n"
	    "</methodResponse>\n" % data
	    )
    return data


def loads(data):
    # convert an XML-RPC packet to data plus a method name (None
    # if not present).  if the XML-RPC packet represents a fault
    # condition, this function raises a Fault exception.
    p, u = getparser()
    p.feed(data)
    p.close()
    return u.close(), u.getmethodname()




# ===================================================================
# Import required extensions
# XXX: try to wrap this like the sgmlop --gafton
from cgiwrap import Input, Output, InputStream


# --------------------------------------------------------------------
# Peek and repackage xmlrpc data.
# XXX: Kludge alert... seems to work ok, but....
def peek(headers, dataFo):
    #'''
    # Function that allows one to get and decode xmlrpc data that is
    # passing thru. This requires us to:
    #       (1) dataFo (myStringI object) needs to have its StringIO
    #       object initiallized, (2) decode, (3) un-xml it,
    #       (4) return decoded xml with method name.
    #'''
    dataFo.memString()
    _resp = Input(headers)
    _fo = _resp.decode(dataFo)
    dataFo.seek(0)
    _decodedData = _fo.read()
    data, method = loads(_decodedData)
    data = data[0]
    return data, method


# --------------------------------------------------------------------
# request dispatcher

class Transport:
    """Handles an HTTP transaction to an XML-RPC server"""
    
    # client identifier (may be overridden)
    user_agent = "xmlrpclib.py/%s" % __version__

    def __init__(self, type="http", refreshCallback=None,
                protocol="HTTP/1.0"):
        self.__lang = "C"
        self.__type = type
        self.__ca_chain = None
        self.__transfer = 0
        self.__encoding = 0
	self.__additional_headers = {}
	self.refreshCallback = refreshCallback
        self.protocol = protocol
        # The output class
        self.__output = None

    # reset the transport options
    def set_transport(self, transfer = 0, encoding = 0):
        self.__transfer = transfer
        self.__encoding = encoding

    # Add arbitrary additional headers.
    def add_header(self, name, arg):
	self.__additional_headers[name] = str(arg)
       
    def request(self, host, proxy, handler,
                request_body, username=None, password=None,
                protocol='HTTP/1.0',
                auth_username=None, auth_password=None):
	# issue XML-RPC request
        # XXX: automatically compute how to send depending on how much data
        #      you want to send

        if self.__type == "raw":
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(host)
            sock.send(request_body)
            sock.send("\r\n\r\n")
            file = sock.makefile('rb')
            return self.parse_response(file)
        
        protocol = string.upper(protocol)
        if protocol[:5] != 'HTTP/': protocol = 'HTTP/1.0'
        httplib.HTTP_VERSION = protocol
        
        #req = Output(Output.TRANSFER_BASE64, Output.ENCODE_ZLIB)
        if not self.__output:
            self.__output = Output(self.__transfer, self.__encoding) 
        req = self.__output
        
	# Add those extra headers.
	for each in self.__additional_headers.keys():
	    req.add_header(each, self.__additional_headers[each])

	# required by XML-RPC
        req.add_header("User-Agent", self.user_agent)
        req.add_header("Content-Type", "text/xml")
        if auth_username and auth_password:
            req.auth_username = auth_username
            req.auth_password = auth_password
            userpass = "%s:%s" % (req.auth_username, req.auth_password)
            enc_userpass = string.strip(base64.encodestring(userpass))
            req.add_header("Authorization", " Basic %s" % enc_userpass)
        if username and password:
            req.username = username
            req.password = password
            userpass = "%s:%s" % (req.username, req.password)
            # this is for proxying of non-ssl connections. ssl connections
            # are "tunneled" and require a slightly different approach
            enc_userpass = string.strip(base64.encodestring(userpass))
            req.add_header("Proxy-Authorization", " Basic %s" % enc_userpass)
        if not self.__lang == "C":
            req.add_header("Accept-Language", self.__lang)
        req.use_CA_chain(self.__ca_chain)
        req.process(request_body)
        
        # XXX: should try-catch ProtocolError here. But I am not sure what to do with it
        # if I get it, so for now letting it slip through to the next level is sortof
        # working. Must be fixed before ship, though. --gafton
        headers, fd = req.send_http(host, proxy, handler, self.__type, 
            protocol=self.protocol)

        if 0:
            print "THE HEADERS COMING IN (xmlrpclib.py):"
            for each in headers.keys():
                print "\t%s : %s" % (each, headers[each])

        # Now use the Input class in case we get an enhanced response
        resp = Input(headers)       
        # this is both sick and swift
        try:
            fd = resp.decode(fd)
        except InputStream, e:           
            return File(e.fd, e.length, e.name)
        return self.parse_response(fd)
        
    def parse_response(self, f):
        # read response from input file, and parse it
	p, u = getparser()
	while 1:
	    response = f.read(1024)
	   
	    if not response:
		break
	    if self.refreshCallback:
		self.refreshCallback()
	    p.feed(response)
	f.close()
	p.close()
	return u.close()

    def setlang(self, lang):
        self.__lang = lang

    def use_CA_chain(self, ca_chain = None):
        self.__ca_chain = ca_chain
        
    def close(self):
        if self.__output:
            self.__output.close()
            self.__output = None

class _Method:
    # some magic to bind an XML-RPC method to an RPC server.
    # supports "nested" methods (e.g. examples.getStateName)
    def __init__(self, send, name):
	self.__send = send
	self.__name = name
    def __getattr__(self, name):
	return _Method(self.__send, "%s.%s" % (self.__name, name))
    def __call__(self, *args):
	return self.__send(self.__name, args)


class Server:
    """Represents a connection to an XML-RPC server""" #"

    def __init__(self, uri, proxy=None, transport=None, refreshCallback=None, 
            username=None, password=None, protocol="HTTP/1.0",
            auth_username=None, auth_password=None):
	# establish a "logical" server connection

        # Set the transport protocol
        self.__protocol = protocol
	# get the url
	type, uri = urllib.splittype(uri)
        if type:
            if not string.lower(type) in ["http", "https"]:
                raise IOError, "unsupported XML-RPC protocol"

            self.__host = urllib.splithost(uri)[0]
            if proxy:
                self.__proxy = proxy
            else:
                self.__proxy = None
            
            self.__handler = type + ":" + uri
            
            if transport is None:
                transport = Transport(string.lower(type),
                                      refreshCallback=refreshCallback,
                                      protocol=self.__protocol)
        else:
            self.__host = uri;
            
            if transport is None:
                transport = Transport("raw",
                                      refreshCallback=refreshCallback)
                                     
        self.__transport = transport
        self.__lang = "C"
        self.__username = username
        self.__password = password
        self.__auth_username = auth_username
        self.__auth_password = auth_password
        self.__ca_chain = None

    def __del__(self):
        self.close()
        
    def __request(self, methodname, params):
	# call a method on the remote server

	request = dumps(params, methodname)

        if hasattr(self.__transport, "setlang"):
            self.__transport.setlang(self.__lang)
            
        if hasattr(self.__transport, "use_CA_chain"):
            self.__transport.use_CA_chain(self.__ca_chain)
            
	response = self.__transport.request(
	    self.__host,
            self.__proxy,
	    self.__handler,
	    request,
            self.__username,
            self.__password,
            self.__protocol,
            self.__auth_username,
            self.__auth_password
	    )

	if type(response) == type(()) and len(response) == 1:
	    response = response[0]

	return response

    def set_transport(self, transfer = 0, encoding = 0):
        if self.__transport:
            self.__transport.set_transport(transfer, encoding)

    # Allow user-defined additional headers.
    def add_header(self, name, arg):
	if self.__transport:
	    self.__transport.add_header(name, arg)

    def set_protocol(self, protocol):
        self.__protocol = string.upper(protocol)
    
    def __repr__(self):
	return "<XML-RPC Server for '%s' with proxy '%s'>" % (
            self.__handler, self.__proxy)

    __str__ = __repr__

    def setlang(self, lang):
        self.__lang = lang
        
    def use_CA_chain(self, ca_chain = None):
        self.__ca_chain = ca_chain
        
    def __getattr__(self, name):
	# magic method dispatcher
	return _Method(self.__request, name)

    def close(self):
        if self.__transport:
            self.__transport.close()
            self.__transport = None

if __name__ == "__main__":

    # simple test program (from the XML-RPC specification)
    # server = Server("http://localhost:8000") # local server

    server = Server("http://betty.userland.com")

    print server

    try:
	print server.examples.getStateName(5)
    except Error, v:
	print "ERROR", v
