rcexecdir = $(bindir)
rcexec_DATA = rc

rcsupportdir = $(datadir)/rc
rcsupport_DATA = 		\
	rcchannelcmds.py	\
	rccommand.py		\
	rcformat.py		\
	rclogcmds.py		\
	rcpackagecmds.py	\
	rcsystemcmds.py		\
	rctalk.py		\
	ximian_xmlrpclib.py

install-exec-hook:
	chmod 0755 $(rcexecdir)/$(rcexec_DATA)
