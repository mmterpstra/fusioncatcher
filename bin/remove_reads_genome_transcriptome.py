#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Given two MAP files, generated by BOWTIE, as input it removes the reads from the second input file which map worse than in the first file.

This is intended to be used for removing the short reads which map on transcriptome worse than on the genome. Worse means a larger number of mismatches.



Author: Daniel Nicorici, Daniel.Nicorici@gmail.com

Copyright (c) 2009-2020 Daniel Nicorici

This file is part of FusionCatcher.

FusionCatcher is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

FusionCatcher is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with FusionCatcher (see file 'COPYING.txt').  If not, see
<http://www.gnu.org/licenses/>.

By default, FusionCatcher is running BLAT aligner
<http://users.soe.ucsc.edu/~kent/src/> but it offers also the option to disable
all its scripts which make use of BLAT aligner if you choose explicitly to do so.
BLAT's license does not allow to be used for commercial activities. If BLAT
license does not allow to be used in your case then you may still use
FusionCatcher by forcing not use the BLAT aligner by specifying the option
'--skip-blat'. Fore more information regarding BLAT please see its license.

Please, note that FusionCatcher does not require BLAT in order to find
candidate fusion genes!

This file is not running/executing/using BLAT.
"""


import sys
import os
import optparse
import gc
import shutil
import tempfile

def give_me_temp_filename(tmp_dir):
    if tmp_dir and (not os.path.isdir(tmp_dir)) and (not os.path.islink(tmp_dir)):
        os.makedirs(tmp_dir)
    (ft,ft_name) = tempfile.mkstemp(dir = tmp_dir)
    os.close(ft)
    return ft_name

def giveRC(h,col):
    return (h[0],h[col])

def map2dict(a_file, column, limit_counts_reads = 7*(10**7), size_buffer = 10**8):
    # get read name and mismatches
    fi = open(a_file,'r')
    pack = None
    last_read = None
    base = []
    while True:
        gc.disable()
        du = fi.readlines(size_buffer)
        gc.enable()
        if not du:
            break
        gc.disable()
        du = [giveRC(d.rstrip('\r\n').split('\t'),column) for d in du]
        gc.enable()
        di = []
        for d in du:
            if last_read != d[0]:
                gc.disable()
                di.append((d[0],0 if not d[1] else d[1].count(':')))
                gc.enable()
                last_read = d[0]
        if di:
            gc.disable()
            base.extend(di)
            gc.enable()
            di = []
        if len(base) > limit_counts_reads:
            gc.disable()
            base = dict(base)
            gc.enable()
            yield base
            base = []
    if base:
        gc.disable()
        base = dict(base)
        gc.enable()
        yield base
        base = []
    fi.close()


if __name__ == '__main__':

    #command line parsing

    usage = "%prog [options]"
    description = """Given two MAP files, generated by BOWTIE, as input it
removes the reads from the second one which map worse than in the first file.
This is intended to be used for removing the short reads which map on
transcriptome worse than on the genome. Worse means a larger number of mismatches.
Both MAP files are assumed to contain only the best mappings of a given read (one read
is found to be mapping on the best stratum which gives the minimum number of
mismatches therefore no read which has several mappings with several different
mismatches)."""
    version = "%prog 0.10 beta"

    parser = optparse.OptionParser(usage = usage,
                                   description = description,
                                   version = version)

    parser.add_option("--input_map_1",
                      action="store",
                      type="string",
                      dest="map_1_filename",
                      help="""The input file in BOWTIE MAP format.""")

    parser.add_option("--input_map_2",
                      action="store",
                      type="string",
                      dest="map_2_filename",
                      help="""The input file in BOWTIE MAP format.""")

    parser.add_option("--mismatches_column",
                      action="store",
                      type="int",
                      dest="mismatches_column",
                      default = 8,
                      help="""The column number in the MAP file which contains the mismatches. Default is %default.""")

    parser.add_option("--output",
                      action="store",
                      type="string",
                      dest="output_filename",
                      help="""The output BOWTIE MAP file. It contains only the reads and their mappings as they appear in '--input_map_2' file except the reads which are found to have a larger number of mismatches in '--input_map_2' file compared to '--input_map_1' file.""")

    parser.add_option("--tmp_dir",
                  action="store",
                  type="string",
                  dest="tmp_dir",
                  default = None,
                  help = "The directory which should be used as temporary directory. By default is the OS temporary directory.")

    (options,args) = parser.parse_args()

    # validate options
    if not (options.map_1_filename and
            options.map_2_filename and
            options.output_filename
            ):
        parser.print_help()
        sys.exit(1)


# Columns' description of the MAP output file:
#    1.      Name of read that aligned
#    2.      Reference strand aligned to, + for forward strand, - for reverse
#    3.      Name of reference sequence where alignment occurs, or numeric ID if no name was provided
#    4.      0-based offset into the forward reference strand where leftmost character of the alignment occurs
#    5.      Read sequence (reverse-complemented if orientation is -). If the read was in colorspace, then the sequence shown in this column is the sequence of decoded nucleotides, not the original colors. See the Colorspace alignment section for details about decoding. To display colors instead, use the --col-cseq option.
#    6.      ASCII-encoded read qualities (reversed if orientation is -). The encoded quality values are on the Phred scale and the encoding is ASCII-offset by 33 (ASCII char !). If the read was in colorspace, then the qualities shown in this column are the decoded qualities, not the original qualities. See the Colorspace alignment section for details about decoding. To display colors instead, use the --col-cqual option.
#    7.      If -M was specified and the prescribed ceiling was exceeded for this read, this column contains the value of the ceiling, indicating that at least that many valid alignments were found in addition to the one reported. Otherwise, this column contains the number of other instances where the same sequence aligned against the same reference characters as were aligned against in the reported alignment. This is not the number of other places the read aligns with the same number of mismatches. The number in this column is generally not a good proxy for that number (e.g., the number in this column may be '0' while the number of other alignments with the same number of mismatches might be large).
#    8.      Comma-separated list of mismatch descriptors. If there are no mismatches in the alignment, this field is empty. A single descriptor has the format offset:reference-base>read-base. The offset is expressed as a 0-based offset from the high-quality (5') end of the read.


    # running
    print "Starting..."
    mc = options.mismatches_column - 1

    # genome
    # 250,858,502 lines => ~8GB
    in1 = options.map_2_filename
    ou1 = give_me_temp_filename(options.tmp_dir)
    final = open(options.output_filename,'w')
    first_flag = True
    lastread = None
    lastappended = False
    lastfinal = False
    for baza in map2dict(options.map_1_filename,mc):
        print "Reading ...",options.map_2_filename
        fin = open(in1,'r')
        fout = open(ou1,'w')
        while True:
            gc.disable()
            lines = fin.readlines(10**8)
            gc.enable()
            if not lines:
                break
            data = []
            data_final = []
            for line in lines:
                gc.disable()
                r = line.rstrip('\r\n').split('\t')
                gc.enable()
                rr = r[0]
                # keep only the reads with their minimum mismatches
                if lastread == rr:
                    if not lastappended:
                        continue
                    elif lastfinal:
                        data_final.append(line)
                    else:
                        data.append(line)
                else:
                    lastread = rr
                    if baza.has_key(rr):
                        m = 0 if not r[mc] else r[mc].count(':')
                        if baza[rr] >= m:
                            gc.disable()
                            data_final.append(line)
                            gc.enable()
                            lastappended = True
                            lastfinal = True
                        else:
                            lastappended = False
                    else:
                        gc.disable()
                        data.append(line)
                        gc.enable()
                        lastappended = True
                        lastfinal = False
            if data:
                fout.writelines(data)
            if data_final:
                final.writelines(data_final)
            data = []
            data_final = []
        fin.close()
        fout.close()
        if first_flag:
            first_flag = False
        else:
            os.remove(in1)
        in1 = ou1
        ou1 = give_me_temp_filename(options.tmp_dir)
    os.remove(ou1)
    fin = file(in1,'r')
    while True:
        gc.disable()
        lines = fin.readlines(10**8)
        gc.enable()
        if not lines:
            break
        gc.disable()
        final.writelines(lines)
        gc.enable()
    fin.close()
    final.close()
    if not first_flag:
        os.remove(in1)


    print "The end."
