
import os, string
from distutils.core import setup, Extension

pc = os.popen("pkg-config --cflags-only-I glib-2.0", "r")
glib_includes = map(lambda x:x[2:], string.split(pc.readline()))
pc.close()

pc = os.popen("pkg-config --libs-only-l glib-2.0", "r")
glib_libs = map(lambda x:x[2:], string.split(pc.readline()))
pc.close()

pc = os.popen("pkg-config --libs-only-L glib-2.0", "r")
glib_libdirs = map(lambda x:x[2:], string.split(pc.readline()))
pc.close()

module1 = Extension('ximian_unmarshaller',
                    define_macros = [('MAJOR_VERSION', '0'),
                                     ('MINOR_VERSION', '1')],
                    include_dirs = glib_includes,
                    libraries = glib_libs,
                    library_dirs = glib_libdirs,
                    sources = ['unmarshaller.c'])

setup (name = 'ximian_unmarshaller',
       version = '0.1',
       description = 'A fast unmarshaller',
       author = 'Rupert',
       author_email = 'rupert@ximian.com',
       url = 'http://www.ximian.com',
       long_description = '''
It is an unmarshaller.  Hopefully it is fast.,
''',
       ext_modules = [module1])
