rugexecdir = $(bindir)
rugexec_DATA = rug

rugsupportdir = $(datadir)/rug
rugsupport_DATA = 		\
	rcchannelutils.py	\
	rccommand.py		\
	rcfault.py		\
	rcformat.py		\
	rcmain.py		\
	rcpackageutils.py	\
	rctalk.py		\
	rcutil.py		\
	ximian_xmlrpclib.py

rugcmdsdir = $(rugsupportdir)/commands
rugcmds_DATA = 		\
	rcchannelcmds.py	\
	rclockcmds.py		\
	rclogcmds.py		\
	rcnewscmds.py		\
	rcpackagecmds.py	\
	rcprefscmds.py		\
	rcsystemcmds.py	\
	rctransactcmds.py	\
	rcusercmds.py		\
	rcwhatcmds.py		\
	rcmountcmds.py

EXTRA_DIST = $(rugsupport_DATA) $(rugcmds_DATA)

install-exec-hook:
	chmod 0755 $(DESTDIR)$(rugexecdir)/$(rugexec_DATA)
