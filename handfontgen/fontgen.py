#!/usr/bin/env/python3
# coding: utf-8
# ちゃんとutf-8で開いてくれよ>エディター

import sys
import tempfile
import shutil
import os

#from util import getgrayimage
import util

import scanchars
import fontgenfromsvg


def main(argv):
    if len(argv) < 3:
        print("Usage: %s dest.otf pic_src [pic_src ...]\n"%argv[0]
            +"       source.txt is a text file which conains chars you want to make form into.\n"
            +"       dest.pdf is a path for a output pdf file.")
        quit()
    
    destfile = argv[1]
    sources = argv[2:]
    
    #this metadata should be indivisual setting file like .ini or xml? 
    # metadata = generatefontfromsvg.FontMetaData.fromsvgfile(filename)
    metadata = generatefontfromsvg.FontMetaData(
            fontname="TekitounaTegakiFont", 
            family="TekitounaTegakiFont", 
            fullname="TekitounaTegakiFont", 
            weight="Regular", 
            copyrightnotice="(c) nixeneko 2016 http://nixeneko.hatenablog.com , generated with FontForge", 
            fontversion="1.00", 
            familyJP="適当な手書きフォント",
            fullnameJP="適当な手書きフォント",
            ascent=860,
            descent=140
            )
    svgdir = tempfile.mkdtemp() #tempdir
    
    try:
        #make svg files from scanned forms
        scanchars.addfiles(sources, svgdir) 
        #generate opentype font
        generatefontfromsvg.generatefont(destfile, metadata, svgdir)
    except:
        shutil.rmtree(svgdir)
        raise
    finally:
        if os.path.isdir(svgdir):
            shutil.rmtree(svgdir)

if __name__ == '__main__':
    main(sys.argv)