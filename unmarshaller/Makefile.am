
unmarshallerdir = $(libdir)/rc

unmarshaller_DATA = ximian_unmarshaller.so

# Boy, that mv build/lib.*/ construction sure is lame.
ximian_unmarshaller.so: setup.py unmarshaller.c
	rm -rf build
	python ./setup.py build
	mv build/lib.*/ximian_unmarshaller.so .

EXTRA_DIST = $(unmarshaller_DATA) setup.py unmarshaller.c