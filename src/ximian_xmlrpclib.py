#
# XML-RPC CLIENT LIBRARY
#
# an XML-RPC client interface for Python.
#
# the marshalling and response parser code can also be used to
# implement XML-RPC servers.
#
# Notes:
# this version is designed to work with Python 1.5.2 or newer.
# unicode encoding support requires at least Python 1.6.
# experimental HTTPS requires Python 2.0 built with SSL sockets.
# expat parser support requires Python 2.0 with pyexpat support.
#
# History:
# 1999-01-14 fl  Created
# 1999-01-15 fl  Changed dateTime to use localtime
# 1999-01-16 fl  Added Binary/base64 element, default to RPC2 service
# 1999-01-19 fl  Fixed array data element (from Skip Montanaro)
# 1999-01-21 fl  Fixed dateTime constructor, etc.
# 1999-02-02 fl  Added fault handling, handle empty sequences, etc.
# 1999-02-10 fl  Fixed problem with empty responses (from Skip Montanaro)
# 1999-06-20 fl  Speed improvements, pluggable parsers/transports (0.9.8)
# 2000-11-28 fl  Changed boolean to check the truth value of its argument
# 2001-02-24 fl  Added encoding/Unicode/SafeTransport patches
# 2001-02-26 fl  Added compare support to wrappers (0.9.9/1.0b1)
# 2001-03-28 fl  Make sure response tuple is a singleton
# 2001-03-29 fl  Don't require empty params element (from Nicholas Riley)
# 2001-06-10 fl  Folded in _xmlrpclib accelerator support (1.0b2)
# 2001-08-20 fl  Base xmlrpclib.Error on built-in Exception (from Paul Prescod)
# 2001-09-03 fl  Allow Transport subclass to override getparser
# 2001-09-10 fl  Lazy import of urllib, cgi, xmllib (20x import speedup)
# 2001-10-01 fl  Remove containers from memo cache when done with them
# 2001-10-01 fl  Use faster escape method (80% dumps speedup)
# 2001-10-10 sm  Allow long ints to be passed as ints if they don't overflow
# 2001-10-17 sm  test for int and long overflow (allows use on 64-bit systems)
# 2001-11-12 fl  Use repr() to marshal doubles (from Paul Felix)
# 2002-07-02 js  Forward-ported my HTTP Basic auth support and Unix domain
#                socket support.
#
# Copyright (c) 1999-2001 by Secret Labs AB.
# Copyright (c) 1999-2001 by Fredrik Lundh.
# Copyright (c) 2002 Ximian, Inc.
#
# info@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The XML-RPC client interface is
#
# Copyright (c) 1999-2001 by Secret Labs AB
# Copyright (c) 1999-2001 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

#
# things to look into:

# TODO: support basic authentication (see robin's patch)
# TODO: fix host tuple handling in the server constructor
# TODO: let transport verify schemes
# TODO: update documentation
# TODO: authentication plugins

"""
An XML-RPC client interface for Python.

The marshalling and response parser code can also be used to
implement XML-RPC servers.

Exported exceptions:

  Error          Base class for client errors
  ProtocolError  Indicates an HTTP protocol error
  ResponseError  Indicates a broken response package
  Fault          Indicates an XML-RPC fault package

Exported classes:

  ServerProxy    Represents a logical connection to an XML-RPC server

  Boolean        boolean wrapper to generate a "boolean" XML-RPC value
  DateTime       dateTime wrapper for an ISO 8601 string or time tuple or
                 localtime integer value to generate a "dateTime.iso8601"
                 XML-RPC value
  Binary         binary data wrapper

  Marshaller     Generate an XML-RPC params chunk from a Python data structure
  Transport      Handles an HTTP transaction to an XML-RPC server
  SafeTransport  Handles an HTTPS transaction to an XML-RPC server

Exported constants:

  True
  False

Exported functions:

  boolean        Convert any Python value to an XML-RPC boolean
  dumps          Convert an argument tuple or a Fault instance to an XML-RPC
"""

import re, socket, string, time, operator
import ximian_unmarshaller
import threading
from types import *

try:
    unicode
except NameError:
    unicode = None # unicode support not available

def _decode(data, encoding, is8bit=re.compile("[\x80-\xff]").search):
    # decode non-ascii string (if possible)
    if unicode and encoding and is8bit(data):
        data = unicode(data, encoding)
    return data

def escape(s, replace=string.replace):
    s = replace(s, "&", "&amp;")
    s = replace(s, "<", "&lt;")
    return replace(s, ">", "&gt;",)

MAXINT =  2L**31-1
MININT = -2L**31

if unicode:
    def _stringify(string):
        # convert to 7-bit ascii if possible
        try:
            return str(string)
        except UnicodeError:
            return string
else:
    def _stringify(string):
        return string

__version__ = "1.0.0"

# --------------------------------------------------------------------
# Exceptions

class Error(Exception):
    """Base class for client errors."""
    def __str__(self):
        return repr(self)

class ProtocolError(Error):
    """Indicates an HTTP protocol error."""
    def __init__(self, url, errcode, errmsg, headers):
        Error.__init__(self)
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
    """Indicates a broken response package."""
    pass

class Fault(Error):
    """Indicates an XML-RPC fault package."""
    def __init__(self, faultCode, faultString, **extra):
        Error.__init__(self)
        self.faultCode = faultCode
        self.faultString = faultString
    def __repr__(self):
        return (
            "<Fault %s: %s>" %
            (self.faultCode, repr(self.faultString))
            )

# --------------------------------------------------------------------
# Special values

class Boolean:
    """Boolean-value wrapper.

    Use True or False to generate a "boolean" XML-RPC value.
    """

    def __init__(self, value = 0):
        self.value = operator.truth(value)

    def encode(self, out):
        out.write("<value><boolean>%d</boolean></value>\n" % self.value)

    def __cmp__(self, other):
        if isinstance(other, Boolean):
            other = other.value
        return cmp(self.value, other)

    def __repr__(self):
        if self.value:
            # return "<Boolean True at %x>" % id(self)
            return "True"
        else:
            # return "<Boolean False at %x>" % id(self)
            return "False"

    def __int__(self):
        return self.value

    def __nonzero__(self):
        return self.value

True, False = Boolean(1), Boolean(0)

def boolean(value, truefalse=(False, True)):
    """Convert any Python value to XML-RPC 'boolean'."""
    return truefalse[operator.truth(value)]

class DateTime:
    """DateTime wrapper for an ISO 8601 string or time tuple or
    localtime integer value to generate 'dateTime.iso8601' XML-RPC
    value.
    """

    def __init__(self, value=0):
        if not isinstance(value, StringType):
            if not isinstance(value, TupleType):
                if value == 0:
                    value = time.time()
                value = time.localtime(value)
            value = time.strftime("%Y%m%dT%H:%M:%S", value)
        self.value = value

    def __cmp__(self, other):
        if isinstance(other, DateTime):
            other = other.value
        return cmp(self.value, other)

    def __repr__(self):
        return "<DateTime %s at %x>" % (self.value, id(self))

    def decode(self, data):
        self.value = string.strip(data)

    def encode(self, out):
        out.write("<value><dateTime.iso8601>")
        out.write(self.value)
        out.write("</dateTime.iso8601></value>\n")

def datetime(data):
    value = DateTime()
    value.decode(data)
    return value

class Binary:
    """Wrapper for binary data."""

    def __init__(self, data=None):
        self.data = data

    def __cmp__(self, other):
        if isinstance(other, Binary):
            other = other.data
        return cmp(self.data, other)

    def decode(self, data):
        import base64
        self.data = base64.decodestring(data)

    def encode(self, out):
        import base64, StringIO
        out.write("<value><base64>\n")
        base64.encode(StringIO.StringIO(self.data), out)
        out.write("</base64></value>\n")

def binary(data):
    value = Binary()
    value.decode(data)
    return value

WRAPPERS = DateTime, Binary, Boolean


#
# HTTP helper functions
#
# it is very lame this isn't in httplib.

def parse_http_list(s):
    """Parse lists as described by RFC 2068 Section 2.

    In particular, parse comman-separated lists where the elements of
    the list may include quoted-strings.  A quoted-string could
    contain a comma.
    """
    # XXX this function could probably use more testing

    list = []
    end = len(s)
    i = 0
    inquote = 0
    start = 0
    while i < end:
        cur = s[i:]
        c = string.find(cur, ',')
        q = string.find(cur, '"')
        if c == -1:
            list.append(s[start:])
            break
        if q == -1:
            if inquote:
                raise ValueError, "unbalanced quotes"
            else:
                list.append(s[start:i+c])
                i = i + c + 1
                continue
        if inquote:
            if q < c:
                list.append(s[start:i+c])
                i = i + c + 1
                start = i
                inquote = 0
            else:
                i = i + q
        else:
            if c < q:
                list.append(s[start:i+c])
                i = i + c + 1
                start = i
            else:
                inquote = 1
                i = i + q + 1
    return map(lambda x:string.strip(x), list)

def parse_keqv_list(l):
    """Parse list of key=value strings where keys are not duplicated."""
    parsed = {}
    for elt in l:
        k, v = string.split(elt, '=', 1)
        if v[0] == '"' and v[-1] == '"':
            v = v[1:-1]
        parsed[k] = v
    return parsed

# --------------------------------------------------------------------
# XML-RPC marshalling and unmarshalling code

class Marshaller:
    """Generate an XML-RPC params chunk from a Python data structure.

    Create a Marshaller instance for each set of parameters, and use
    the "dumps" method to convert your data (represented as a tuple)
    to an XML-RPC params chunk.  To write a fault response, pass a
    Fault instance instead.  You may prefer to use the "dumps" module
    function for this purpose.
    """

    # by the way, if you don't understand what's going on in here,
    # that's perfectly ok.

    def __init__(self, encoding=None):
        self.memo = {}
        self.data = None
        self.encoding = encoding

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
            # FIXME: the xml-rpc specification allows us to leave out
            # the entire <params> block if there are no parameters.
            # however, changing this may break older code (including
            # old versions of xmlrpclib.py), so this is better left as
            # is for now.  See @XMLRPC3 for more information. /F
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

    def dump_boolean(self, value):
        self.write("<value><boolean>%d</boolean></value>\n" % value)

    try:
        dispatch[BooleanType] = dump_boolean
    except NameError:
        ## Boolean type is only present in 2.3+
        pass

    def dump_int(self, value):
        # in case ints are > 32 bits
        if value > MAXINT or value < MININT:
            raise OverflowError, "int exceeds XML-RPC limits"
        self.write("<value><int>%s</int></value>\n" % value)
    dispatch[IntType] = dump_int

    def dump_long(self, value):
        # in case ints are > 32 bits
        if value > MAXINT or value < MININT:
            raise OverflowError, "long int exceeds XML-RPC limits"
        self.write("<value><int>%s</int></value>\n" % int(value))
    dispatch[LongType] = dump_long

    def dump_double(self, value):
        self.write("<value><double>%s</double></value>\n" % repr(value))
    dispatch[FloatType] = dump_double

    def dump_string(self, value, escape=escape):
        self.write("<value><string>%s</string></value>\n" % escape(value))
    dispatch[StringType] = dump_string

    if unicode:
        def dump_unicode(self, value, escape=escape):
            value = value.encode(self.encoding)
            self.write("<value><string>%s</string></value>\n" % escape(value))
        dispatch[UnicodeType] = dump_unicode

    def opencontainer(self, value):
        if value:
            i = id(value)
            if self.memo.has_key(i):
                raise TypeError, "cannot marshal recursive data structures"
            self.memo[i] = None

    def closecontainer(self, value):
        if value:
            del self.memo[id(value)]

    def dump_array(self, value):
        self.opencontainer(value)
        write = self.write
        dump = self.__dump
        write("<value><array><data>\n")
        for v in value:
            dump(v)
        write("</data></array></value>\n")
        self.closecontainer(value)
    dispatch[TupleType] = dump_array
    dispatch[ListType] = dump_array

    def dump_struct(self, value, escape=escape):
        self.opencontainer(value)
        write = self.write
        dump = self.__dump
        write("<value><struct>\n")
        for k, v in value.items():
            write("<member>\n")
            if type(k) is not StringType:
                raise TypeError, "dictionary key must be string"
            write("<name>%s</name>\n" % escape(k))
            dump(v)
            write("</member>\n")
        write("</struct></value>\n")
        self.closecontainer(value)
    dispatch[DictType] = dump_struct

    def dump_instance(self, value):
        # check for special wrappers
        if value.__class__ in WRAPPERS:
            value.encode(self)
        else:
            # store instance attributes as a struct (really?)
            self.dump_struct(value.__dict__)
    dispatch[InstanceType] = dump_instance

# --------------------------------------------------------------------
# convenience functions

def dumps(params, methodname=None, methodresponse=None, encoding=None):
    """data [,options] -> marshalled data

    Convert an argument tuple or a Fault instance to an XML-RPC
    request (or response, if the methodresponse option is used).

    In addition to the data object, the following options can be given
    as keyword arguments:

        methodname: the method name for a methodCall packet

        methodresponse: true to create a methodResponse packet.
        If this option is used with a tuple, the tuple must be
        a singleton (i.e. it can contain only one element).

        encoding: the packet encoding (default is UTF-8)

    All 8-bit strings in the data structure are assumed to use the
    packet encoding.  Unicode strings are automatically converted,
    where necessary.
    """

    assert isinstance(params, TupleType) or isinstance(params, Fault),\
           "argument must be tuple or Fault instance"

    if isinstance(params, Fault):
        methodresponse = 1
    elif methodresponse and isinstance(params, TupleType):
        assert len(params) == 1, "response tuple must be a singleton"

    if not encoding:
        encoding = "utf-8"

    m = Marshaller(encoding)
    data = m.dumps(params)

    if encoding != "utf-8":
        xmlheader = "<?xml version='1.0' encoding=%s?>\n" % repr(encoding)
    else:
        xmlheader = "<?xml version='1.0'?>\n" # utf-8 is default

    # standard XML-RPC wrappings
    if methodname:
        # a method call
        if not isinstance(methodname, StringType):
            methodname = methodname.encode(encoding)
        data = (
            xmlheader,
            "<methodCall>\n"
            "<methodName>", methodname, "</methodName>\n",
            data,
            "</methodCall>\n"
            )
    elif methodresponse:
        # a method response, or a fault structure
        data = (
            xmlheader,
            "<methodResponse>\n",
            data,
            "</methodResponse>\n"
            )
    else:
        return data # return as is
    return string.join(data, "")

# --------------------------------------------------------------------
# request dispatcher

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

class Transport:
    """Handles an HTTP transaction to an XML-RPC server."""

    # client identifier (may be overridden)
    user_agent = "xmlrpclib.py/%s (by www.pythonware.com)" % __version__

    __auth_data = None
    tried_once = 0

    def __init__(self):
        self.__cancelled = []

    def request(self, host, handler, request_body, verbose=0,
                username=None, password=None):
        # issue XML-RPC request

        h = self.make_connection(host)
        if verbose:
            h.set_debuglevel(1)

        if verbose:
            print "request:", repr(request_body)

        self.send_request(h, handler, request_body)
        self.send_host(h, host)
        self.send_user_agent(h)
        if self.__auth_data:
            self.send_auth(h)

        self.send_content(h, request_body)

        errcode, errmsg, headers = h.getreply()

        if errcode == 401 and not self.tried_once:
            auth = headers.getheader("WWW-Authenticate")
            if auth and username and password:
                if self.generate_auth(auth, handler, username, password):
                    self.tried_once = 1
                    r = self.request(host, handler, request_body, verbose,
                                     username, password)
                    self.tried_once = 0
                    return r

        if errcode != 200:
            raise ProtocolError(
                host + handler,
                errcode, errmsg,
                headers
                )

        self.verbose = verbose

        return self.parse_response(h.getfile())

    def make_connection(self, host):
        # create a HTTP connection object from a host descriptor
        import httplib
        try:
            return httplib.HTTP(host)
        except ValueError:
            # This is lame.  The Python 2.2 httplib seems to have
            # regressed.  Before if you passed in a nonnumeric port
            # you'd get a socket.error exception telling you so.  Now
            # httplib just spews an invalid literal error on int().
            from socket import error
                
            raise error, "nonnumeric port"
        
    def send_request(self, connection, handler, request_body):
        connection.putrequest("POST", handler)

    def send_host(self, connection, host):
        connection.putheader("Host", host)

    def send_user_agent(self, connection):
        connection.putheader("User-Agent", self.user_agent)

    def send_content(self, connection, request_body):
        connection.putheader("Content-Type", "text/xml")
        connection.putheader("Content-Length", str(len(request_body)))
        connection.endheaders()
        if request_body:
            connection.send(request_body)

    def send_auth(self, connection):
        connection.putheader("Authorization", self.__auth_data)

    def generate_auth(self, auth, handler, username, password):
        type, auth_data = string.split(auth, None, 1)
        if type == "Digest":
            auth_fn = self.generate_digest
        elif type == "Basic":
            auth_fn = self.generate_basic
        else:
            return 0

        auth_fn(auth_data, handler, username, password)
        return 1

    def generate_basic(self, auth, handler, username, password):
        import base64

        userpass = username + ":" + password
        enc_userpass = string.strip(base64.encodestring(userpass))
        self.__auth_data = "Basic %s" % enc_userpass

    def generate_digest(self, auth, handler, username, password):
        import md5
        import os

        # FIXME: This only does the MD5 algorithm (not MD5-sess) and
        # only the "auth" qop (quality of protection), not "auth-int"

        auth_info = parse_keqv_list(parse_http_list(auth))

        import rcutil

        A1 = rcutil.hexstr(md5.new(username + ":" +
                                   auth_info["realm"] + ":" +
                                   password).digest())
        A2 = rcutil.hexstr(md5.new("POST:" + handler).digest())

        cnonce = rcutil.hexstr(md5.new("%s:%s:%s" % (str(self),
                                                     str(os.getpid()),
                                                     str(time.time()))).digest())
        
        response = rcutil.hexstr(md5.new(A1 + ":" + auth_info["nonce"] +
                                         ":00000001:" + cnonce +
                                         ":auth:" + A2).digest())

        self.__auth_data = 'Digest username="%s", realm="%s", nonce="%s", ' \
                           'cnonce="%s", nc=00000001, qop=auth, uri="%s", ' \
                           'response="%s"' % (username, auth_info["realm"],
                                              auth_info["nonce"], cnonce,
                                              handler, response)
        

    def cancel(self, thread):
        self.__cancelled.append(thread)

    def parse_response(self, f):
        # read response from input file, and parse it

        def binary_cb(data):
            b = Binary()
            b.decode(data)
            return b
        def boolean_cb(value):
            if value == 0:
                return False
            elif value == 1:
                return True
            else:
                raise TypeError, "bad boolean value"
        def fault_cb(arg):
            raise apply(Fault, (), arg)

        my_thread = threading.currentThread()
        unmarshaller = ximian_unmarshaller.new(binary_cb, boolean_cb, fault_cb)
        first_pass = 1
        while 1:
            if my_thread in self.__cancelled:
                f.close()
                self.__cancelled.remove(my_thread)
                return ()
            response = f.read(1024)
            if not response:
                break

            if self.verbose:
                print "response:", repr(response)

            # FIXME: This is evil and wrong and papers over what appears
            # to be a race in rcd.  Essentially there is garbage on the
            # wire, including null bytes, and the unmarshaller will throw
            # a TypeError if this happens, so we move past the bad data
            # to the start of the actual XML
            if first_pass:
                ind = string.index(response, "<?xml")
                if self.verbose and ind > 0:
                    print "Moving past %d bad bytes" % ind
                response = response[ind:]

            unmarshaller.feed(response, 0)

            first_pass = 0

        f.close()
        unmarshaller.feed("", 1)
        return unmarshaller.close()


class SafeTransport(Transport):
    """Handles an HTTPS transaction to an XML-RPC server."""

    def make_connection(self, host):
        # create a HTTPS connection object from a host descriptor
        # host may be a string, or a (host, x509-dict) tuple
        import httplib
        if isinstance(host, TupleType):
            host, x509 = host
        else:
            x509 = {}
        try:
            HTTPS = httplib.HTTPS
        except AttributeError:
            raise NotImplementedError,\
                  "your version of httplib doesn't support HTTPS"
        else:
            try:
                return apply(HTTPS, (host, None), x509)
            except ValueError:
                # This is lame.  The Python 2.2 httplib seems to have
                # regressed.  Before if you passed in a nonnumeric port
                # you'd get a socket.error exception telling you so.  Now
                # httplib just spews an invalid literal error on int().
                from socket import error
                
                raise error, "nonnumeric port"

    def send_host(self, connection, host):
        if isinstance(host, TupleType):
            host, x509 = host
        connection.putheader("Host", host)

class RawTransport(Transport):

    def request(self, host, handler, request_body, verbose=0,
                username=None, password=None):
        self.verbose = verbose
        
        sock = self.make_connection(host)

        if verbose:
            print "request:", repr(request_body)

        self.send_content(sock, request_body)

        file = sock.makefile("rb")
        sock.close()

        return self.parse_response(file)
    
    def make_connection(self, host):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(host)

        return sock

    def send_content(self, sock, request_body):
        sock.send(request_body)
        sock.send("\r\n\r\n")

class ServerProxy:
    """uri [,options] -> a logical connection to an XML-RPC server

    uri is the connection point on the server, given as
    scheme://host/target.

    The standard implementation always supports the "http" scheme.  If
    SSL socket support is available (Python 2.0), it also supports
    "https".

    If the target part and the slash preceding it are both omitted,
    "/RPC2" is assumed.

    The following options can be given as keyword arguments:

        transport: a transport factory
        encoding: the request encoding (default is UTF-8)

    All 8-bit strings passed to the server proxy are assumed to use
    the given encoding.
    """

    def __init__(self, uri, transport=None, encoding=None, verbose=0,
                 auth_username=None, auth_password=None):
        # establish a "logical" server connection

        # get the url
        import urllib
        type, uri = urllib.splittype(uri)
        if type:
            if type not in ("http", "https"):
                raise IOError, "unsupported XML-RPC protocol"
            self.__host, self.__handler = urllib.splithost(uri)
            if not self.__handler:
                self.__handler = "/RPC2"

            if transport is None:
                if type == "https":
                    transport = SafeTransport()
                else:
                    transport = Transport()
        else:
            self.__host = uri
            transport = RawTransport()
            
        self.__transport = transport

        self.__encoding = encoding
        self.__verbose = verbose

        self.__username = auth_username
        self.__password = auth_password

    def __request(self, methodname, params):
        # call a method on the remote server

        request = dumps(params, methodname, encoding=self.__encoding)

        response = self.__transport.request(
            self.__host,
            self.__handler,
            request,
            verbose=self.__verbose,
            username=self.__username,
            password=self.__password
            )

        if len(response) == 1:
            response = response[0]

        return response

    def __repr__(self):
        return (
            "<ServerProxy for %s%s>" %
            (self.__host, self.__handler)
            )

    __str__ = __repr__

    def __getattr__(self, name):
        # magic method dispatcher
        return _Method(self.__request, name)

    # note: to call a remote object with an non-standard name, use
    # result getattr(server, "strange-python-name")(args)

    def cancel(self, thread):
        self.__transport.cancel(thread)

    def set_username(self, username):
        self.__username = username

    def set_password(self, password):
        self.__password = password

# compatibility
Server = ServerProxy

# --------------------------------------------------------------------
# test code

if __name__ == "__main__":

    # simple test program (from the XML-RPC specification)

    # server = ServerProxy("http://localhost:8000") # local server
    server = ServerProxy("http://betty.userland.com")

    print server

    try:
        print server.examples.getStateName(41)
    except Error, v:
        print "ERROR", v
