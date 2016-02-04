#!/usr/bin/env/python3
# coding: utf-8
# ちゃんとutf-8で開いてくれよ>エディター

from xml.etree import ElementTree
import re, codecs, math
#import numpy as np
#import cv2
import copy
#import random
import io
import os
import base64
import qrcode
import cairosvg
import PyPDF2

TEMPLATEFILEREL = '../resources/charbox_template_5-8-5.svg'
PAPERTEMPLATEREL = '../resources/a4paper_marker.svg'

pathbase = os.path.dirname(os.path.abspath(__file__))
TEMPLATEFILE = os.path.normpath(os.path.join(pathbase, TEMPLATEFILEREL))
PAPERTEMPLATE = os.path.normpath(os.path.join(pathbase, PAPERTEMPLATEREL))

A4WIDTH_MM = 210

class Rect():
    def __init__(self, x, y, w, h, dpmm=2.835):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.dpmm = dpmm
        
    def __str__(self):
        return "(x: {}, y: {}, w: {}, h: {})".format(self.x, self.y, self.w, self.h)
        
    def addoffset(self, offset):
        return Rect(self.x + offset[0], self.y + offset[1], self.w, self.h)
        
    def mm(self): # rect in mm
        return Rect(round(self.x / self.dpmm),
                    round(self.y / self.dpmm),
                    round(self.w / self.dpmm),
                    round(self.h / self.dpmm))

class TemplateTiler:
    SVGNS = "http://www.w3.org/2000/svg"
    def __init__(self):
        self.tilegroup = None
        self.tilesize = None
        self.rectscanarea = None
        self.rectdrawarea = None
        self.rectqrarea = None
        self.textpos = None
        self.tiledpmm = 2.83
    
    def _getsize(self, elem):
        try:
            width = float(elem.get("width", default="0").split("px")[0])
            height = float(elem.get("height", default="0").split("px")[0])
            assert width != 0, "the given element has no width!"
            assert height != 0, "the given element has no height!"
        except:
            raise ValueError("<svg>'s width should be like '595.28' or '595.28px'")
        return width, height
        
    def _getpos(self, elem):
        x = float(elem.get("x"))
        y = float(elem.get("y"))
        return x, y
        
    def _getrectfromelem(self, elem, conv="px", dpmm=2.83):
        x, y = self._getpos(elem)
        w, h = self._getsize(elem)
        
        return Rect(x, y, w, h, dpmm)
            
    def _getmaxrowcol(self, area, tile, inbetween=0, margin=(0,0,0,0)):
        #margin: (top, right, bottom, left)
        margint, marginr, marginb, marginl = margin
        ncol = math.floor((area.w -marginr-marginl) / (tile[0]+inbetween))
        while ncol * tile[0] + (ncol-1) * inbetween > area.w - marginr - marginl:
            ncol -= 1
        nrow = math.floor((area.h -margint-marginb) / (tile[1]+inbetween))
        while nrow * tile[1] + (nrow-1) * inbetween > area.h - margint - marginb:
            nrow -= 1
        return ncol, nrow
    
    def loadtiletemplate(self, src):
        ElementTree.register_namespace('', self.SVGNS)
        
        xmltree = ElementTree.parse(src)
        xmlroot = xmltree.getroot()
        a4pxwidth, a4pxheight = self._getsize(xmlroot)
        # dot per mm
        dpmm = a4pxwidth / A4WIDTH_MM
        self.tiledpmm = dpmm
        #print(a4pxwidth, dpmm)
        
        self.tilegroup = xmlroot.find(".//*[@id='tilegroup']")
        assert self.tilegroup.tag == "{%s}g"%self.SVGNS, "<g id=tilegroup> not found"
        
        # remove id
        #self.tilegroup.attrib.pop("id")
        
        # get the width and the height of the template area
        tilearea = self.tilegroup.find(".//*[@id='tilearea']")
        #assert tilearea, "<rect id=tilearea> not found" 
        assert tilearea.tag == "{%s}rect"%self.SVGNS, "<rect id=tilearea> not found"
        
        self.tilesize = self._getsize(tilearea)
        
        # get the rectangle area that are cropped
        scanarea = self.tilegroup.find(".//*[@id='scanarea']")
        assert scanarea.tag == "{%s}rect"%self.SVGNS, "<rect id=scanarea> not found"
        
        self.rectscanarea = self._getrectfromelem(scanarea, dpmm)
        
        # get the rectangle area where pictures are drawn
        drawarea = self.tilegroup.find(".//*[@id='drawarea']")
        assert drawarea.tag == "{%s}rect"%self.SVGNS, "<rect id=drawarea> not found"
        
        self.rectdrawarea = self._getrectfromelem(drawarea, dpmm)
        
        # get the rectangle area where the QR-code are placed
        qrarea = self.tilegroup.find(".//*[@id='qrarea']")
        assert qrarea.tag == "{%s}rect"%self.SVGNS, "<rect id=qrarea> not found"
        
        self.rectqrarea = self._getrectfromelem(qrarea, dpmm)
        
        # get the position where the text is placed
        textplace = self.tilegroup.find(".//*[@id='textplace']")
        assert textplace.tag == "{%s}text"%self.SVGNS, "<text id=textplace> not found"
        textplace.text = ""
        if "x" in textplace.attrib and "y" in textplace.attrib:
            strtextx, strtexty = self._getpos(textplace)
        else:
            # when designated by tranform attrib
            strtransform = textplace.get("transform")
            p = re.compile(r"""matrix\(\d+\.?\d*\s+\d+\.?\d*\s+\d+\.?\d*\s+\d+\.?\d*\s+(\d+\.?\d*)\s+(\d+\.?\d*)\)""")
            match = p.search(strtransform)
            assert match, "No position is assigned for the text placeholder"
            strtextx = match.group(1)
            strtexty = match.group(2)
        self.textpos = (float(strtextx), float(strtexty))
        
    def _getqrtag(self, text, rect):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image()
        bio = io.BytesIO()
        img.save(bio)
        
        pngqr = bio.getvalue()
        base64qr = base64.b64encode(pngqr)
        #<image x="110" y="20" width="280px" height="160px" xlink:href="data:image/png;base64,……"/>
        imagetag = ElementTree.Element("image")
        imagetag.set("xlink:href", "data:image/png;base64,"+base64qr.decode("ascii"))
        imagetag.set("x", str(rect.x))
        imagetag.set("y", str(rect.y))
        imagetag.set("width", str(rect.w))
        imagetag.set("height", str(rect.h))
        return imagetag
        
    def outputtemplateonepage(self, listchar):
        ElementTree.register_namespace('', self.SVGNS)
        ElementTree.register_namespace('xlink', "http://www.w3.org/1999/xlink")
        
        with open(PAPERTEMPLATE, 'r') as f:
            strsvg = f.read()
        strdeclaration = strsvg[:strsvg.find("<svg")]
        
        xmltree = ElementTree.parse(PAPERTEMPLATE)
        xmlroot = xmltree.getroot()
        xmlroot.set('xmlns:xlink', "http://www.w3.org/1999/xlink")
        #print(xmlroot.attrib)
        
        a4pxwidth, a4pxheight = self._getsize(xmlroot)
        dpmm = a4pxwidth / A4WIDTH_MM
        #TODO size conversion is needed in case DPI of the two SVG files not matched.
        assert dpmm == self.tiledpmm, "DPI not matched"
        
        # calclulate how many columns and rows can be inserted
        placeholder = xmlroot.find(".//*[@id='placeholder']")
        assert placeholder.tag == "{%s}rect"%self.SVGNS, "<rect id=placeholder> not found"
        rectph = self._getrectfromelem(placeholder)
        
        inbetween = 3.0 * dpmm  # 3mm
        margin = (3.0 * dpmm, 0 * dpmm, 3 * dpmm, 2.0 * dpmm) # t,r,b,l
        ncol, nrow = self._getmaxrowcol(rectph, self.tilesize, inbetween, margin)
       
        
        #if xmlroot has <defs> tag, append tile group to it. if not, create <defs>.
        defstag = xmlroot.find('{%s}defs'%self.SVGNS)
        
        if not defstag:
            defstag = ElementTree.Element("defs") # or {self.SVGNS}defs ?
            xmlroot.append(defstag)
        
        defstag.append(self.tilegroup)
        
        # maybe it's better to do centering
        for ny in range(nrow):
            for nx in range(ncol):
                posx = rectph.x + margin[3] + nx*(self.tilesize[0]+inbetween)
                posy = rectph.y + margin[0] + ny*(self.tilesize[1]+inbetween)
                if ny == nrow - 1 and nx == ncol - 1: #right bottom corner
                    a = self.rectdrawarea.mm() #inside
                    A = self.rectscanarea.mm() #outside
                    qrstr = "{:d}:{:d}:{:d},{:d}:{:d}:{:d}".format(
                        a.x - A.x, a.w, A.x + A.w - a.x - a.w,
                        a.y - A.y, a.h, A.y + A.h - a.y - a.h)
                    qrrect = self.rectscanarea.addoffset((posx, posy))
                    imagetag = self._getqrtag(qrstr, qrrect)
                    xmlroot.append(imagetag)
                    continue
                #<use xlink:href="#tilegroup" x="10" y="10"/>
                usetag = ElementTree.Element("use")
                usetag.set("xlink:href", "#tilegroup")
                usetag.set("x", str(posx))
                usetag.set("y", str(posy))
                xmlroot.append(usetag)
                
                if listchar:
                    c = listchar.pop(0)
                    #TODO if (str, glyphname) is given instead of str in the list,
                    # the function will set strname as a printed text, and glyphname for
                    # the QR code
                    if isinstance(c, str):
                        texttag = ElementTree.Element("text")
                        texttag.text = c
                        texttag.set("style", "font-size:10pt;")
                        texttag.set("x", str(posx + self.textpos[0]))
                        texttag.set("y", str(posy + self.textpos[1]))
                        xmlroot.append(texttag)
                        
                        qrstr = "{:4X}".format(ord(c))
                        qrrect = self.rectqrarea.addoffset((posx, posy))
                        imagetag = self._getqrtag(qrstr, qrrect)
                        xmlroot.append(imagetag)
                    else:
                        continue
        
        rectsize = inbetween
        for ny in range(1,nrow):
            posx = rectph.x
            posy = rectph.y + margin[0] + ny*(self.tilesize[1]+inbetween) - inbetween/2
            linetag = ElementTree.Element("line")
            linetag.set("style", "stroke:#B9FFFF;stroke-width:0.2835;")
            linetag.set("x1", str(posx))
            linetag.set("y1", str(posy))
            linetag.set("x2", str(posx+rectph.w))
            linetag.set("y2", str(posy))
            xmlroot.append(linetag)
            recttag = ElementTree.Element("rect")
            recttag.set("style", "fill:#000000;")
            recttag.set("x", str(posx-rectsize/2))
            recttag.set("y", str(posy-rectsize/2))
            recttag.set("width", str(rectsize))
            recttag.set("height", str(rectsize))
            xmlroot.append(recttag)
        for nx in range(1,ncol):
            posx = rectph.x + margin[3] + nx*(self.tilesize[0]+inbetween) - inbetween/2
            posy = rectph.y 
            linetag = ElementTree.Element("line")
            linetag.set("style", "stroke:#B9FFFF;stroke-width:0.2835;")
            linetag.set("x1", str(posx))
            linetag.set("y1", str(posy))
            linetag.set("x2", str(posx))
            linetag.set("y2", str(posy+rectph.h))
            xmlroot.append(linetag)
            recttag = ElementTree.Element("rect")
            recttag.set("style", "fill:#000000;")
            recttag.set("x", str(posx-rectsize/2))
            recttag.set("y", str(posy-rectsize/2))
            recttag.set("width", str(rectsize))
            recttag.set("height", str(rectsize))
            xmlroot.append(recttag)
            
        # write svg
        bstrxml = ElementTree.tostring(xmlroot, method='xml')
        outsvg = strdeclaration.replace("iso-8859-1","utf-8").encode('utf-8') + bstrxml
        
        iopdf = io.BytesIO()
        cairosvg.svg2pdf(bytestring=outsvg, write_to=iopdf, dpi=self.tiledpmm*25.4)
        iopdf.seek(0, io.SEEK_SET)
        return iopdf
        #with open(dest, 'wb') as w:
            #print(strdeclaration)
        #    w.write(strdeclaration.replace("iso-8859-1","utf-8").encode('utf-8'))
        #    w.write(bstrxml)

    def outputpapertemplate(self, dest, listchar):
        output = PyPDF2.PdfFileWriter()
        while listchar:
            iopage = self.outputtemplateonepage(listchar)
            page = PyPDF2.PdfFileReader(iopage)
            output.addPage(page.getPage(0))
        with open(dest, "wb") as w:
            output.write(w)
        
def main():
    listchar = list("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよわゐゑをんぁぃぅぇぉがぎぐげござじずぜぞだぢづでどっばびぶべぼぱぴぷぺぽゃゅょ")
    t = TemplateTiler()
    t.loadtiletemplate(TEMPLATEFILE)
    t.outputpapertemplate('test.pdf', listchar)
    
            
if __name__ == '__main__':
    main()