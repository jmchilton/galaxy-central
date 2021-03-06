#!/usr/bin/env python2.4
#%prog bounding_region_file mask_intervals_file intervals_to_mimic_file out_file mask_chr mask_start mask_end interval_chr interval_start interval_end


from __future__ import division 

import pkg_resources
pkg_resources.require( "bx-python" )

import sys, random
import bisect
from bx.bitset import *

def throw_random_2( lengths, mask ):
    """
    Version of throw using gap lists (like Hiram's randomPlacement). This 
    is not ready yet!!!
    """
    # Projected version for throwing
    bits = BitSet( mask.size )
    # Use mask to find the gaps
    gaps = []
    start = end = 0
    while 1:
        start = mask.next_clear( end )
        if start == mask.size: break
        end = mask.next_set( start )
        gaps.append( ( end-start, start, end ) )
    # Sort (long regions first )    
    gaps.sort()
    gaps.reverse()
    # And throw
    for length in lengths:
        max_candidate = 0
        candidate_bases = 0
        for gap in gaps:
            if gap[0] >= length:
                max_candidate += 1
                candidate_bases += ( gap[0] - length )
            else: 
                break
        if max_candidate == 0:
            raise MaxtriesException( "No gap can fit region of length %d" % length )
        # Select start position
        s = random.randrange( candidate_bases )
        # Map back to region
        chosen_index = 0
        for gap in gaps:
            gap_length, gap_start, gap_end = gap
            if s > ( gap_length - length ):
                s -= ( gap_length - length )
                chosen_index += 1
            else:
                break
        # Remove the chosen gap and split
        assert ( gap_length, gap_start, gap_end ) == gaps.pop( chosen_index )
        # gap_length, gap_start, gap_end =  gaps.pop( chosen_index )
        assert s >= 0
        assert gap_start + s + length <= gap_end, "Expected: %d + %d + %d == %d <= %d" % ( gap_start, s, length, gap_start + s + length, gap_end )
        gaps.reverse()
        if s > 0:
            bisect.insort( gaps, ( s, gap_start, gap_start + s ) )
        if s + length < gap_length:
            bisect.insort( gaps, ( gap_length - ( s + length ), gap_start + s + length, gap_end) )
        gaps.reverse()
        # And finally set the bits
        assert bits[gap_start + s] == 0 
        assert bits.next_set( gap_start + s, gap_start+s+length ) == gap_start+s+length 
        assert( gap_start + s >= 0 and gap_start + s + length <= bits.size ), "Bad interval %d %d %d %d %d" % ( gap_start, s, length, gap_start + s + length, bits.size )
        bits.set_range( gap_start + s, length )   
    assert bits.count_range( 0, bits.size ) == sum( lengths )
    return bits

def overlapping_in_bed( fname, r_chr, r_start, r_stop, chr_col, start_col, end_col ):
    rval = []
    for line in open( fname ):
        if line.startswith( "#" ) or line.startswith( "track" ):
            continue
        fields = line.split()
        try:
            chr, start, stop = fields[chr_col], int( fields[start_col] ), int( fields[end_col] )
            if chr == r_chr and start < r_stop and stop >= r_start:
                rval.append( ( chr, max( start, r_start ), min( stop, r_stop ) ) )
        except:
            continue
    return rval        

def as_bits( region_start, region_length, intervals ):
    bits = BitSet( region_length )
    for chr, start, stop in intervals:
        bits.set_range( start - region_start, stop - start )
    return bits

def bit_clone( bits ):
    new = BitSet( bits.size )
    new.ior( bits )
    return new

def count_overlap( bits1, bits2 ):
    b = BitSet( bits1.size )
    b |= bits1
    b &= bits2
    return b.count_range( 0, b.size )

def interval_lengths( bits ):
    end = 0
    while 1:
        start = bits.next_set( end )
        if start == bits.size: break
        end = bits.next_clear( start )
        yield end - start

def main():
    #region_fname = sys.argv[1]
    region_uid = sys.argv[1]
    mask_fname = sys.argv[2]
    intervals_fname = sys.argv[3]
    out_fname = sys.argv[4]
    mask_chr = int(sys.argv[5])-1
    mask_start = int(sys.argv[6])-1
    mask_end = int(sys.argv[7])-1
    interval_chr = int(sys.argv[8])-1
    interval_start = int(sys.argv[9])-1
    interval_end = int(sys.argv[10])-1
    use_mask = sys.argv[11]
    
    available_regions = {}

    loc_file = "/cache/regions/regions.loc"


    try:
        for line in open( loc_file ):
            if line[0:1] == "#" : continue
        
            fields = line.split('\t')
            #read each line, if not enough fields, go to next line
            try:
                build = fields[0]
                uid = fields[1]
                description = fields[2]
                filepath =fields[3].replace("\n","").replace("\r","")
                available_regions[uid]=filepath
            except:
                continue

    except Exception, exc:
        print >>sys.stdout, 'random_intervals.py initialization error -> %s' % exc 

    if region_uid not in available_regions:
        print >>stderr, "Invalid region selected"
        sys.exit(0)
    region_fname = available_regions[region_uid]

    
    out_file = open (out_fname, "w") or die ("Can not open output file")
    try:
        line_count = 0
        for line in open( region_fname ):
            try:
                line_count += 1
                # Load lengths for all intervals overlapping region
                if line[0:1] == "#":
                    continue
                fields = line.split()
                #print >>sys.stderr, "Processing region:", fields[3]
                r_chr, r_start, r_stop = fields[0], int( fields[1] ), int( fields[2] )
                r_length = r_stop - r_start
                # Load the mask
                if use_mask == "no_mask":
                    mask = []
                else:
                    mask = overlapping_in_bed( mask_fname, r_chr, r_start, r_stop, mask_chr, mask_start, mask_end )
                bits_mask = as_bits( r_start, r_length, mask )
                bits_not_masked = bit_clone( bits_mask ); bits_not_masked.invert()
                # Load the first set
                intervals1 = overlapping_in_bed( intervals_fname, r_chr, r_start, r_stop, interval_chr, interval_start, interval_end )
                bits1 = as_bits( r_start, r_length, intervals1 )
                # Intersect it with the mask 
                bits1.iand( bits_not_masked )
                # Sanity checks
                assert count_overlap( bits1, bits_mask ) == 0
                chrom = r_chr
                # For each data set
                lengths1 = list( interval_lengths( bits1 ) )
                random1 = throw_random_2( lengths1, bits_mask )
                end =0
                while 1:
                    start = random1.next_set( end )
                    if start == random1.size: break
                    end = random1.next_clear( start )
                    print >>out_file, "%s\t%d\t%d" % ( chrom, start, end )
            except:
                print >>stderr, "Error on line:", line_count
                continue
    except:
        print >>stderr, "The Region file appears to be missing"

if __name__ == "__main__": main()
