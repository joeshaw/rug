rcexecdir = $(bindir)
rcexec_DATA = rc

rcsupportdir = $(datadir)/rc
rcsupport_DATA = 		\
	rcchannelcmds.py	\
	rcchannelutils.py	\
	rccommand.py		\
	rcformat.py		\
	rclogcmds.py		\
	rcmain.py		\
	rcnewscmds.py		\
	rcpackagecmds.py	\
	rcprefscmds.py		\
	rcsystemcmds.py		\
	rctalk.py		\
	rcwhatcmds.py		\
	ximian_xmlrpclib.py

EXTRA_DIST = $(rcsupport_DATA)

install-exec-hook:
	chmod 0755 $(rcexecdir)/$(rcexec_DATA)
