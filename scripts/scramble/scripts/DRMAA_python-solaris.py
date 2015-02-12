import os, sys, shutil

if "SGE_ROOT" not in os.environ:
    print "main(): Please set SGE_ROOT to the path of your SGE installation"
    print "main(): before scrambling DRMAA_python"
    sys.exit(1)

# change back to the build dir
if os.path.dirname( sys.argv[0] ) != "":
    os.chdir( os.path.dirname( sys.argv[0] ) )

# find setuptools
sys.path.insert( 1, os.path.join( '..', '..', '..', 'lib' ) )
from scramble_lib import *

tag = get_tag() # get the tag
clean() # clean up any existing stuff (could happen if you run scramble.py by hand)

# if our python is 64 bit, use 64 bit sge...
if sys.maxint < ( 2048 * 1024 * 1024 ):
    if sys.byteorder == 'big':
        arch = "sparc"
    else:
        arch = "x86"
else:
    if sys.byteorder == 'big':
        arch = "sparc64"
    else:
        arch = "amd64"

# if we're using sun cc, drop the gcc -Wno-unused option
cc = get_solaris_compiler()

# patch
file = "setup.py"
print "main(): Patching", file
if not os.access( "%s.orig" %file, os.F_OK ):
    shutil.copyfile( file, "%s.orig" %file )
i = open( "%s.orig" %file, "r" )
o = open( file, "w" )
for line in i.readlines():
    if line == 'SGE6_ROOT="/scratch_test02/SGE6"\n':
        line = 'SGE6_ROOT="%s"\n' % os.environ["SGE_ROOT"]
    elif line.startswith('SGE6_ARCH='):
        line = 'SGE6_ARCH="sol-%s"\n' % arch
    elif line.startswith('link_args ='):
        line = 'link_args = [ "-L%s" % os.path.join(SGE6_ROOT, "lib", SGE6_ARCH), "-Wl,-R%s" % os.path.join(SGE6_ROOT, "lib", SGE6_ARCH),  "-ldrmaa"  ]\n'
    if line == "                   + [ '-Wno-unused' ]\n":
        if cc == 'cc':
            line = "                   #+ [ '-Wno-unused' ]\n"
    print >>o, line,
i.close()
o.close()

# reset args for distutils
me = sys.argv[0]
sys.argv = [ me ]
sys.argv.append( "bdist_egg" )

# do it
execfile( "setup.py", globals(), locals() )
