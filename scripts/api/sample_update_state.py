#!/usr/bin/env python


import os, sys, traceback
sys.path.insert( 0, os.path.dirname( __file__ ) )
from common import display
from common import submit
from common import update

try:
    data = {}
    data[ 'update_type' ] = 'sample_state'
    data[ 'sample_ids' ] = sys.argv[3].split(',')
    data[ 'new_state' ] = sys.argv[4]
except IndexError:
    print 'usage: %s key url sample_ids new_state [comment]' % os.path.basename( sys.argv[0] )
    sys.exit( 1 )
try:
    data[ 'comment' ] = sys.argv[5]
except IndexError:
    data[ 'comment' ] = ''

update( sys.argv[1], sys.argv[2], data, return_formatted=True )
