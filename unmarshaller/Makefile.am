
unmarshallerdir = $(libdir)/rug

unmarshaller_DATA = ximian_unmarshaller.so

# Boy, that mv build/lib.*/ construction sure is lame.
ximian_unmarshaller.so: setup.py unmarshaller.c
	rm -rf build
	if [ ! -e unmarshaller.c ]; then	\
		cp $(srcdir)/unmarshaller.c .;	\
	fi
	python $(srcdir)/setup.py build
	mv build/lib.*/ximian_unmarshaller.so .

EXTRA_DIST = setup.py unmarshaller.c

distclean:
	rm -rf build unmarshaller.c ximian_unmarshaller.so

clean:
	rm -rf build ximian_unmarshaller.so
