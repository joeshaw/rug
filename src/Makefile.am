rcexecdir = $(bindir)
rcexec_DATA = rc

rcsupportdir = $(datadir)/rc
rcsupport_DATA = 		\
	rcchannelcmds.py	\
	rcchannelutils.py	\
	rccommand.py		\
	rcfault.py		\
	rcformat.py		\
	rclockcmds.py		\
	rclogcmds.py		\
	rcmain.py		\
	rcnewscmds.py		\
	rcpackagecmds.py	\
	rcpackageutils.py	\
	rcprefscmds.py		\
	rcsystemcmds.py		\
	rctalk.py		\
	rctransactcmds.py	\
	rcutil.py		\
	rcusercmds.py		\
	rcwhatcmds.py		\
	rcmountcmds.py		\
	ximian_xmlrpclib.py

EXTRA_DIST = $(rcsupport_DATA)

install-exec-hook:
	chmod 0755 $(DESTDIR)$(rcexecdir)/$(rcexec_DATA)
