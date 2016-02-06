#!/usr/bin/env/python3
# coding: utf-8
# ちゃんとutf-8で開いてくれよ>エディター

import sys
import codecs
import os
import argparse
import io

import tilecharbox

TEMPLATEFILEREL = "../resources/charbox_template_5-8-5.svg"
pathbase = os.path.dirname(os.path.abspath(__file__))
TEMPLATEFILE = os.path.normpath(os.path.join(pathbase, TEMPLATEFILEREL))
def remdup(seq):
    seen = set()
    seen_add = seen.add
    return [ x for x in seq if x not in seen and not seen_add(x)]
    
def formgen(dest, template, files):
    strcharset = ""
    for fname in files:
        with codecs.open(fname, "r", "utf-8") as f:
            strcharset += f.read()
    strcharset = strcharset.replace(" ", "").replace("\n", "").replace("\r", "")
    
    lstchar = remdup(list(strcharset))
    
    t = tilecharbox.TemplateTiler()
    t.loadtiletemplate(template)
    t.outputpapertemplate(dest, lstchar)
    
def hanzentxt2pdfform(hankakutxt, zenkakutxt):
    hankakutemp = "../resources/charbox_template_5-8-5_5-4-5.svg"
    zenkakutemp = "../resources/charbox_template_5-8-5.svg"
    lsthankaku = remdup(list(hankakutxt.replace(" ", "").replace("\n", "").replace("\r", "")))
    lstzenkaku = remdup(list(zenkakutxt.replace(" ", "").replace("\n", "").replace("\r", "")))

    iobin = io.BytesIO()
    t = tilecharbox.TemplateTiler()
    t.loadtiletemplate(os.path.normpath(os.path.join(pathbase, hankakutemp)))
    pdfw = t.outputpapertemplate(None, lsthankaku)
    t.loadtiletemplate(os.path.normpath(os.path.join(pathbase, zenkakutemp)))
    t.outputpapertemplate(iobin, lstzenkaku, output=pdfw)
    return iobin.getvalue()
            
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate a form on which characters to be written.')
    parser.add_argument('-o', metavar='dest.pdf', dest='dest', default='out.pdf',
                    help='output pdf file')
    parser.add_argument('-t', metavar='template.svg', dest='template', default=TEMPLATEFILE,
                    help='template svg file') 
    parser.add_argument('files', metavar='file', nargs='+',
                    help='text files that contains characters to be on a generated form')

    args = parser.parse_args()

    formgen(args.dest, args.template, args.files)
    
    