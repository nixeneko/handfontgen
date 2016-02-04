#!/usr/bin/env/python3
# coding: utf-8
# ちゃんとutf-8で開いてくれよ>エディター

import sys
import codecs

import tilecharbox

TEMPLATEFILE = "resources/charbox_template_5-8-5.svg"

def main(argv):
    argc = len(argv)
    if argc != 3:
        print("Usage: %s source.txt dest.pdf\n"%argv[0]
            +"       source.txt is a text file which conains chars you want to make form into.\n"
            +"       dest.pdf is a path for a output pdf file.")
        quit()
    
    strcharset = ""
    with codecs.open(argv[1], "r", "utf-8") as f:
        strcharset = f.read()
    strcharset = strcharset.replace(" ", "").replace("\n", "").replace("\r", "")
    
    lstchar = list(strcharset)
    
    t = tilecharbox.TemplateTiler()
    t.loadtiletemplate(TEMPLATEFILE)
    t.outputpapertemplate(argv[2], lstchar)
    
            
if __name__ == '__main__':
    main(sys.argv)