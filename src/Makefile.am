rugexecdir = $(bindir)
rugexec_DATA = rug

rugsupportdir = $(datadir)/rug
rugsupport_DATA = 		\
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

EXTRA_DIST = $(rugsupport_DATA)

install-exec-hook:
	chmod 0755 $(DESTDIR)$(rugexecdir)/$(rugexec_DATA)
