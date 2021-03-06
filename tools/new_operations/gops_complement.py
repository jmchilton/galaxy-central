#!/usr/bin/env python

"""
Complement regions.

usage: %prog in_file out_file
    -1, --cols1=N,N,N,N: Columns for chrom, start, end, strand in file
    -d, --db=N: Database name (for determining chromosome lengths)
    -a, --all: Complement all chromosomes (Genome-wide complement)
"""

import pkg_resources
pkg_resources.require( "bx-python" )

import sys
import traceback
import fileinput
from warnings import warn

from bx.intervals import *
from bx.intervals.io import *
from bx.intervals.operations.complement import complement
from bx.intervals.operations.subtract import subtract
import cookbook.doc_optparse

from galaxyops import *

def main():
    allchroms = False
    upstream_pad = 0
    downstream_pad = 0

    options, args = cookbook.doc_optparse.parse( __doc__ )
    try:
        chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols1 )
        db = options.db
        if options.all: allchroms = True
        in_fname, out_fname = args
    except:
        cookbook.doc_optparse.exception()

    g1 = GenomicIntervalReader( fileinput.FileInput( in_fname ),
                                chrom_col=chr_col_1,
                                start_col=start_col_1,
                                end_col=end_col_1,
                                strand_col=strand_col_1)
        
    out_file = open( out_fname, "w" )
    lens = dict()
    chroms = list()
    dbfile = fileinput.FileInput( "static/ucsc/chrom/"+db+".len" )
    
    if dbfile:
        if not allchroms:
            try:
                for line in dbfile:
                    fields = line.split("\t")
                    lens[fields[0]] = int(fields[1])
            except:
                # assume LEN doesn't exist or is corrupt somehow
                pass
        elif allchroms:
            try:
                for line in dbfile:
                    fields = line.split("\t")
                    end = int(fields[1])
                    chroms.append("\t".join([fields[0],"0",str(end)]))
            except:
                pass

    # Safety...if the dbfile didn't exist and we're on allchroms, then
    # default to generic complement
    if allchroms and len(chroms) == 0:
        allchroms = False

    if allchroms:
        chromReader = GenomicIntervalReader(chroms)
        generator = subtract([chromReader, g1])
    else:
        generator = complement(g1, lens)
        
    for interval in generator:
        if type( interval ) is GenomicInterval:
            print >> out_file, "\t".join( interval )
        else:
            print >> out_file, interval

if __name__ == "__main__":
    main()
