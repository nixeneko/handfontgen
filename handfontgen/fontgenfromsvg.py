#!/usr/bin/env/python3
# coding: utf-8
# ちゃんとutf-8で開いてくれよ>エディター

#import numpy as np
#import cv2
#import copy
#import random
import glob
import re
import os
from xml.etree import ElementTree
import subprocess
import sys
import codecs
import argparse

#from util import getgrayimage
import util

# command path
FONTFORGE = "fontforge"

GLYPHFILE = "*.svg"

CYGWINFLG = util.checkcygwin()
CYGPATHFLG = True       # set True when using Cygwin Fontforge

# for debugging
SCRIPT_WRITE_FILE_FLG = False
SCRIPT_FILENAME = 'script.pe'

class FontMetaData():
    def __init__(self, fontname="", family="", fullname="", 
                 weight="", copyrightnotice="", fontversion="", 
                 familyJP="", fullnameJP="", 
                 ascent=800, descent=200):
        self.fontname = fontname
        self.family = family
        self.fullname = fullname
        self.weight = weight
        self.copyrightnotice = copyrightnotice
        self.fontversion = fontversion
        self.familyJP = familyJP
        self.fullnameJP = fullnameJP
        self.ascent = ascent
        self.descent = descent
        
    def fromxmlfile(filename):
        xmltree = ElementTree.parse(filename)
        xmlroot = xmltree.getroot()
        
        ddict = {}
        for data in xmlroot:
            ddict[data.tag] = data.text
        
        if 'ascent' in ddict:
            ddict['ascent'] = int(ddict['ascent'])
        if 'descent' in ddict:
            ddict['descent'] = int(ddict['descent'])
        
        return FontMetaData(**ddict)

class SVGGlyph():
    RE_HEX = re.compile("""^[0-9A-Z]+$""", re.IGNORECASE)
    def __init__(self, name, width, path):
        self.name = name
        if self.RE_HEX.match(name):
            if 2 <= len(name) < 4:
                self.uname = "u" + "0" * (4 - len(name)) + name
            else:
                self.uname = "u" + name
        else:
            self.uname = name
        self.width = int(width)
        # workaround for using cygwin fontforge
        if CYGWINFLG and CYGPATHFLG and os.path.isabs(path):
            self.path = util.cygpathconv(util.escapepath(path))
        else:
            self.path = util.escapepath(path)
        
def generateffscript(dest, metadata, lstglf, codepoints):
    script  = '#!/usr/bin/env fontforge -script\n\n'

    script += 'New();\n\n'

    script += 'ScaleToEm({ascent},{descent})\n\n'.format(
                            ascent = metadata.ascent,
                            descent = metadata.descent)
    
    script += '# make .notdef\n'
    script += 'Select(0x0000);\n'
    script += 'SetWidth(1000);\n'
    script += 'SetGlyphName(".notdef");\n\n'

    script += '# use Unicode encoding\n'
    script += 'Reencode("unicode");\n\n'

    # import svg here
    script += '# import SVG files\n'
    script += 'Print("importing svg files...");\n'
    
    # define U+0020 space if not defined
    if 0x20 not in codepoints:
        script += 'Select(0u0020);\n'
        script += 'SetWidth(500);\n'
        
    # define U+3000 Ideographic Space if not defined
    if 0x3000 not in codepoints:
        script += 'Select(0u3000);\n'
        script += 'SetWidth(1000);\n'
        
    for glf in lstglf:
        #script += 'Print("{name}");\n'.format(name=glf.name)
        script += 'Select("{uname}");\n'.format(uname=glf.uname)
        script += 'Import("{path}", 0);\n'.format(path=glf.path)
        script += 'SetWidth({width});\n'.format(width=glf.width)

    # WAVE DASH <-> FULLWIDTH TILDE conversion
    if 0x301c in codepoints and 0xff5e not in codepoints:
        script += 'Select(0u301c);\n'
        script += 'Copy();\n'
        script += 'Select(0uff5e);\n'
        script += 'Paste();\n'
    elif 0x301c not in codepoints and 0xff5e in codepoints:
        script += 'Select(0uff5e);\n'
        script += 'Copy();\n'
        script += 'Select(0u301c);\n'
        script += 'Paste();\n'

    script += '\n'    
    script += '# Auto Hinting off\n'
    script += 'SelectAll();\n'
    script += 'DontAutoHint();\n\n'

    script += '# round to integer values\n'
    script += 'RoundToInt();\n\n'
    
    script += '# set font info\n'
    # SetFontNames(fontname[,family[,fullname[,weight[,copyright-notice[,fontversion]]]]])
    script += 'SetFontNames("{fontname}",\\\n'.format(fontname=metadata.fontname)
    script += '             "{family}",\\\n'.format(family=metadata.family)
    script += '             "{fullname}",\\\n'.format(fullname=metadata.fullname)
    script += '             "{weight}",\\\n'.format(weight=metadata.weight)
    script += '             "{copyright}",\\\n'.format(copyright=metadata.copyrightnotice)
    script += '             "{fontversion}");\n\n'.format(fontversion=metadata.fontversion)

    # SetTTFName(lang,nameid,utf8-string)
    # see https://www.microsoft.com/typography/otspec/name.htm
    script += 'SetTTFName(0x411, 1, "{familyJP}");\n'.format(familyJP=metadata.familyJP)
    script += 'SetTTFName(0x411, 4, "{fullnameJP}");\n\n'.format(fullnameJP=metadata.fullnameJP)

    # workaround for cygwin fontforge
    if CYGWINFLG and CYGPATHFLG and os.path.isabs(dest):
        dest = util.cygpathconv(util.escapepath(dest))
    
    script += '# generate OTF file\n'
    script += 'Generate("{destfile}", "", 0x94);\n'.format(destfile=dest)
    script += 'Print("generated: {destfile}");\n\n'.format(destfile=dest)

    script += 'Close();\n'
    script += 'Quit();\n'

    return script

def passfontforge(strscript, verbose=True): #optionargs=[]
    args = [
        FONTFORGE,
        '-lang=ff', '-script', '-'
    ] #+ optionargs
    
    if verbose:
        p = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            #stdout=subprocess.PIPE,
            #stderr=subprocess.PIPE,
            shell=False
            )
    else:
        p = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False
            )
        
    stdout, stderr = p.communicate(input=strscript.encode("utf-8"))


def readsvgwidth(filename):
    xmltree = ElementTree.parse(filename)
    xmlroot = xmltree.getroot()
    try:
        width = float(xmlroot.get("width", default="0").split("px")[0])
    except:
        raise ValueError("{}: <svg>'s width should be like '1000' or '500.0px'".format(filename))
    return width
    
def generatefont(dest, metadata, glyphdir, verbose=True):
    if not os.path.isdir(glyphdir):
        raise IOError('glyph directory not found!')

    # make output directory if not exists
    outdir = os.path.dirname(dest)
    if outdir != '' and not os.path.isdir(outdir):
        os.makedirs(outdir)
        
    # list up svg files
    wildcard = os.path.join(glyphdir, GLYPHFILE)
    lstfile = glob.glob(wildcard)
        
    # load svg, and check the width of the document, 
    # which will be set to the width of the glyph in a font
    lstglyph = []
    charset = []
    r = re.compile('''^(uni|u|x|0x)?([0-9A-F]+)$''', re.IGNORECASE)
    for file in lstfile:
        basename = os.path.basename(file)
        name, ext = os.path.splitext(basename)
        lstglyph.append(SVGGlyph(name, readsvgwidth(file), file))

        m = r.match(name)
        charcode = int(m.group(2), 16)
        charset.append(charcode)
        
    # import svgs, and generate font using fontforge
    script = generateffscript(dest, metadata, lstglyph, charset)
    if SCRIPT_WRITE_FILE_FLG:
        with codecs.open(SCRIPT_FILENAME, 'w', 'utf-8') as w:
            w.write(script)
    passfontforge(script, verbose)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate a font from SVG files.')
    parser.add_argument('dest', metavar='dest.otf', 
                    help='output pdf file')
    parser.add_argument('srcdir', 
                    help='directory that contains character SVG files')
    parser.add_argument('metadata', nargs='?',
                    help='XML files that contains font meta data')

    args = parser.parse_args()

    if args.metadata:
        metadata = FontMetaData.fromxmlfile(args.metadata)
    else:
        metadata = FontMetaData(
            fontname="TekitounaTegakiFont", 
            family="TekitounaTegakiFont", 
            fullname="TekitounaTegakiFont", 
            weight="Regular", 
            copyrightnotice="generated with FontForge", 
            fontversion="0.01", 
            familyJP="適当な手書きフォント",
            fullnameJP="適当な手書きフォント",
            ascent=860,
            descent=140
            )
    
    generatefont(args.dest, metadata, args.srcdir)
    