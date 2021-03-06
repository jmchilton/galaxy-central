#!/usr/bin/env python2.4

"""
usage: %prog data_file.h5 region_mapping.bed in_file out_file chrom_col start_col end_col [options]
   -p, --perCol: standardize to lod per column
"""

from __future__ import division

import sys
from numarray import *
from numarray.ieeespecial import *
from tables import *

import pkg_resources; pkg_resources.require( "bx-python" )

import cookbook.doc_optparse
from bx import intervals

def main():
    # Parse command line
    options, args = cookbook.doc_optparse.parse( __doc__ )
    try:
        h5_fname = args[0]
        mapping_fname = args[1]
        in_fname = args[2]
        out_fname = args[3]
        chrom_col, start_col, end_col = map( lambda x: int( x ) - 1, args[4:7] )
        per_col = bool( options.perCol )
    except Exception, e:
        print e
        cookbook.doc_optparse.exit()
    # Open the h5 file
    h5 = openFile( h5_fname, mode = "r" )
    # Load intervals and names for the subregions
    intersecters = {}
    for line in open( mapping_fname ):
        chr, start, end, name = line.split()[0:4]
        if not intersecters.has_key( chr ): 
            intersecters[ chr ] = intervals.Intersecter()
        intersecters[ chr ].add_interval( intervals.Interval( int( start ), int( end ), name ) )
    in_file = open( in_fname )
    out_file = open( out_fname, "w" )
    # Find the subregion containing each input interval 
    for index, line in enumerate( in_file ):
        if line.startswith( "#" ):
            if index == 0:
                print >> out_file, line.rstrip() + "\tscore"
            else:
                print >> out_file, line,
        fields = line.rstrip().split( "\t" )
        chr = fields[ chrom_col ]
        start = int( fields[ start_col ] )
        end = int( fields[ end_col ] )
        # Find matching interval
        matches = intersecters[ chr ].find( start, end )
        assert len( matches ) == 1, "Interval must match exactly one target region"
        region = matches[0]
        assert start >= region.start and end <= region.end, "Interval must fall entirely within region"
        region_name = region.value
        rel_start = start - region.start
        rel_end = end - region.start
        assert rel_start < rel_end, "Empty region"
        s = h5.getNode( h5.root, "scores_" + region_name )
        c = h5.getNode( h5.root, "counts_" + region_name )
        score = s[rel_end-1]
        count = c[rel_end-1]
        if rel_start > 0:
            score -= s[rel_start-1]
            count -= c[rel_start-1]
        if per_col: 
            score /= count
        fields.append( str( score ) )
        print >>out_file, "\t".join( fields )
    # Close the file handle
    h5.close()
    in_file.close()
    out_file.close()
        
if __name__ == "__main__": main()
