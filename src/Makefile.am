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
	rcserviceutils.py	\
	rctalk.py		\
	rcutil.py		\
	ximian_xmlrpclib.py


if ENABLE_PATCHES
patch_sources = rcyoucmds.py
else
patch_sources =
endif

rugcmdsdir = $(rugsupportdir)/commands
rugcmds_DATA = 			\
	rcchannelcmds.py	\
	rclockcmds.py		\
	rclogcmds.py		\
	rcmountcmds.py		\
	rcnewscmds.py		\
	rcpackagecmds.py	\
	rcprefscmds.py		\
	rcservicecmds.py	\
	rcsystemcmds.py		\
	rctransactcmds.py	\
	rcusercmds.py		\
	rcwhatcmds.py		\
	rcyoucmds.py		\
	$(patch_sources)


EXTRA_DIST = $(rugsupport_DATA) $(rugcmds_DATA)

install-exec-hook:
	chmod 0755 $(DESTDIR)$(rugexecdir)/$(rugexec_DATA)
