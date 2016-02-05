#!/usr/bin/env/python3
# coding: utf-8
# ちゃんとutf-8で開いてくれよ>エディター

import sys
import tempfile
import shutil
import os
import argparse

#from util import getgrayimage
import util

import scanchars
import fontgenfromsvg

def fontgen(destfile, metadata, sources):
    svgdir = tempfile.mkdtemp() #tempdir
    
    try:
        #make svg files from scanned forms
        scanchars.addfiles(sources, svgdir) 
        #generate opentype font
        fontgenfromsvg.generatefont(destfile, metadata, svgdir)
    except:
        shutil.rmtree(svgdir)
        raise
    finally:
        if os.path.isdir(svgdir):
            shutil.rmtree(svgdir)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate a font from scanned pictures of a special form.')
    parser.add_argument('dest', metavar='dest.otf', 
                    help='a path for a output font file')
    parser.add_argument('-m', metavar='metadata.xml', dest='metadata',
                    help='XML files that contains font meta data')
    parser.add_argument('srcs', metavar='src', nargs='+',
                    help='images or directories that contains scanned images of a special form')
    

    args = parser.parse_args()

    if args.metadata:
        metadata = fontgenfromsvg.FontMetaData.fromxmlfile(args.metadata)
    else:
        metadata = fontgenfromsvg.FontMetaData(
            fontname="TekitounaTegakiFont", 
            family="TekitounaTegakiFont", 
            fullname="TekitounaTegakiFont", 
            weight="Regular", 
            copyrightnotice="", 
            fontversion="0.01", 
            familyJP="適当な手書きフォント",
            fullnameJP="適当な手書きフォント",
            ascent=860,
            descent=140
            )
    
    fontgen(args.dest, metadata, args.srcs)
    