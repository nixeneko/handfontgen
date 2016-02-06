#!/usr/bin/env/python3
# coding: utf-8
# ちゃんとutf-8で開いてくれよ>エディター

import numpy as np
import cv2
import sys, os
#import copy
#import random
import glob
import argparse

import slantcorrection
import passzbar
from tilecharbox import Rect
from util import getgrayimage
import passpotrace

DOCSIZE = (191.7, 278.7)

MARKER_TL_RELPATH = '../resources/marker_tl.png'
MARKER_BR_RELPATH = '../resources/marker_br.png'
MARKER_SIZE = 3 #[mm]
SIZE_THRESH_MM = 2 #[mm] marker size threshold for splitting image 

pathbase = os.path.dirname(os.path.abspath(__file__))
markertlpath = os.path.normpath(os.path.join(pathbase, MARKER_TL_RELPATH))
markerbrpath = os.path.normpath(os.path.join(pathbase, MARKER_BR_RELPATH))

MARKER_TL = cv2.imread(markertlpath, cv2.IMREAD_GRAYSCALE)
MARKER_BR = cv2.imread(markerbrpath, cv2.IMREAD_GRAYSCALE)


def makeupright(image):
    #binarize image
    grayimg = getgrayimage(image)
    ret, binimg = cv2.threshold(grayimg,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    
    # markers which are placed for dividing make 
    # the top line darker than the bottom line
    nwhitefirst = np.count_nonzero(binimg[0,:]) #first line
    nwhitelast = np.count_nonzero(binimg[-1,:]) #last line
    if nwhitefirst <= nwhitelast: # upright
        return image
    else:
        return np.rot90(image, k=2)


def splitimage(image):
    dpmm = min(image.shape[0:2]) / DOCSIZE[0]
    sizethresh = SIZE_THRESH_MM * dpmm
    
    uprightimg = makeupright(image)
    grayimg = getgrayimage(uprightimg)
    
    # top line
    top = grayimg[0,:]
    sepx = [0,]
    ret, binimg = cv2.threshold(top,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    nlabels, labels, stats, centroids = cv2.connectedComponentsWithStats(binimg)
    for i in range(1,nlabels):
        if stats[i,cv2.CC_STAT_AREA] >= sizethresh:
            sepx.append(centroids[i][1])
            
    # left line 
    left = grayimg[:,0]
    sepy = [0,]
    ret, binimg = cv2.threshold(left,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    nlabels, labels, stats, centroids = cv2.connectedComponentsWithStats(binimg)
    for i in range(1,nlabels):
        if stats[i,cv2.CC_STAT_AREA] >= sizethresh:
            sepy.append(centroids[i][1])
    
    # divide into images
    imgs = []
    for iy in range(len(sepy)):
        for ix in range(len(sepx)):
            if iy == len(sepy) - 1:
                if ix == len(sepx) - 1:
                    #right-bottom corner
                    imgs.append(uprightimg[int(sepy[iy]):,int(sepx[ix]):])
                else:
                    #bottom end
                    imgs.append(uprightimg[int(sepy[iy]):,int(sepx[ix]):int(sepx[ix+1])])
            else:
                if ix == len(sepx) - 1:
                    #right end
                    imgs.append(uprightimg[int(sepy[iy]):int(sepy[iy+1]),int(sepx[ix]):])
                else:
                    #others
                    imgs.append(uprightimg[int(sepy[iy]):int(sepy[iy+1]),int(sepx[ix]):int(sepx[ix+1])])
                    
    return imgs
    
def detectresol(img):
    typ, val = passzbar.passzbar(img)
    if typ:
        x, y = val.decode('ascii').strip().split(',')
        xlst = x.split(':')
        ylst = y.split(':')
        return [list(map(int, xlst)), list(map(int, ylst))]
    else:
        #raise RuntimeError("QR Code cannot be detected")
        return None

def getmarkerboundingrect(img, mkpos, mksize):
    buffer = int(mksize * 0.15)
    x = mkpos[0] - buffer
    y = mkpos[1] - buffer
    w = mksize + buffer*2
    h = mksize + buffer*2
    roi = img[y:y+h, x:x+w]
    
    grayroi = getgrayimage(roi)
    ret, binimage = cv2.threshold(grayroi,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    nlabels, labels, stats, centroids = cv2.connectedComponentsWithStats(binimage)
    # stats[0], centroids[0] are for the background label. ignore
    # cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP, cv2.CC_STAT_WIDTH, cv2.CC_STAT_HEIGHT
    lblareas = stats[1:,cv2.CC_STAT_AREA]
    imax = max(enumerate(lblareas), key=(lambda x: x[1]))[0] + 1
    boundingrect = Rect(stats[imax, cv2.CC_STAT_LEFT],
                        stats[imax, cv2.CC_STAT_TOP], 
                        stats[imax, cv2.CC_STAT_WIDTH], 
                        stats[imax, cv2.CC_STAT_HEIGHT])
    return boundingrect.addoffset((x,y))

def getcroppedarea(img, markersize):
    #use template matching to detect area to be cropped
    grayimg = getgrayimage(img)
    # detect top-left marker using template matching
    marker_tl = cv2.resize(MARKER_TL, (markersize, markersize))
    matched = cv2.matchTemplate(grayimg, marker_tl, cv2.TM_CCORR_NORMED) #returns float32
    (minval, maxval, minloc, maxloc) = cv2.minMaxLoc(matched)
    
    mkrect = getmarkerboundingrect(grayimg, maxloc, markersize)
    pos_tl = (mkrect.x+mkrect.w, mkrect.y+mkrect.h)
    #pos_tl = (maxloc[0]+markersize, maxloc[1]+markersize)
    
    # detect bottom-right marker using template matching
    marker_br = cv2.resize(MARKER_BR, (markersize, markersize))
    matched = cv2.matchTemplate(grayimg, marker_br, cv2.TM_CCORR_NORMED) #returns float32
    (minval, maxval, minloc, maxloc) = cv2.minMaxLoc(matched)

    mkrect = getmarkerboundingrect(grayimg, maxloc, markersize)
    pos_br = (mkrect.x, mkrect.y)
    #pos_br = maxloc

    #detect QR code
    qrarea = img[pos_br[1]:,:img.shape[0]-pos_br[1]]
    typ, val = passzbar.passzbar(qrarea)
    
    if not typ:
        return None, None
    strval = val.decode('ascii').strip()
    #print(strval)
    
    #cv2.circle(img, pos_tl, 5, (255, 0, 0), -1)
    #cv2.circle(img, pos_br, 5, (0, 255, 0), -1)
    #print(pos_tl, pos_br
    #cv2.imshow("hoge", img)
    #cv2.imshow("hoge", img[pos_tl[1]:pos_br[1], pos_tl[0]:pos_br[0]])
    # crop and return detected area
    return strval, img[pos_tl[1]:pos_br[1], pos_tl[0]:pos_br[0]]

def getapproxmarkersize(docimg):
    dpmm = docimg.shape[1] / DOCSIZE[0]  #dpmm = width[px]/width[mm]
    return int(MARKER_SIZE * dpmm)
    
def saveasfile(outdir, name, bsvg):
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    outpath = os.path.join(outdir, name+".svg")
    with open(outpath, "wb") as w:
        w.write(bsvg)
    
def scanchars(img, outdir):
    wholeimage = slantcorrection.correctslant(img)
    markersize = getapproxmarkersize(wholeimage)
        
    #dpmm = min(img.shape[0:2]) / DOCSIZE[0]
    imgs = splitimage(wholeimage)
    resol = detectresol(imgs.pop())
    if resol == None:
        print('QR Code for the page cannot be detected. skipping the image')
        return
        
    for im in imgs:
        name, croppedimg = getcroppedarea(im, markersize)
        if name == None:
            continue
        grayimg = getgrayimage(croppedimg)
        ret, binimg = cv2.threshold(grayimg,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        print(name, end=" ")
        sys.stdout.flush()
        #cv2.imwrite("chr/"+name+".jpg", croppedimg)
        imgheight = 1000
        margintop   = int(imgheight * resol[1][0] / resol[1][1]) #-h[px] * (margint[mm]/h[mm])
        marginbottom= int(imgheight * resol[1][2] / resol[1][1]) #-h[px] * (marginb[mm]/h[mm])
        imgwidth = int(imgheight * resol[0][1] / resol[1][1]) #h[px] * (w[mm]/h[mm])
        marginleft  = int(imgheight * resol[0][0] / resol[1][1]) #-h[px] * (marginl[mm]/h[mm])
        marginright = int(imgheight * resol[0][2] / resol[1][1]) #-h[px] * (marginr[mm]/h[mm])
        
        # potrace cannot set size in px when converting to SVG.
        # set size in pt and convert to SVG, after that, replace pt with px
        optargs = [ "-W%dpt"%(imgwidth + marginleft + marginright), 
                    "-H%dpt"%(imgheight + margintop + marginbottom),
                    "-L%dpt"%(- marginleft), "-R%dpt"%(- marginright),
                    "-T%dpt"%(- margintop), "-B%dpt"%(- marginbottom)]
        bsvg = passpotrace.passpotrace(binimg, optargs)
        bsvg = bsvg.replace(b"pt", b"px") # any exceptions?
        
        #save function
        saveasfile(outdir, name, bsvg)
        #break
    print("")

# files that cv2.imread can read.
def getreadableimgfile(pathdir):
    return    glob.glob(os.path.join(pathdir, "*.bmp")) \
            + glob.glob(os.path.join(pathdir, "*.dib")) \
            + glob.glob(os.path.join(pathdir, "*.jpeg")) \
            + glob.glob(os.path.join(pathdir, "*.jpg")) \
            + glob.glob(os.path.join(pathdir, "*.jpe")) \
            + glob.glob(os.path.join(pathdir, "*.jp2")) \
            + glob.glob(os.path.join(pathdir, "*.png")) \
            + glob.glob(os.path.join(pathdir, "*.pbm")) \
            + glob.glob(os.path.join(pathdir, "*.pgm")) \
            + glob.glob(os.path.join(pathdir, "*.ppm")) \
            + glob.glob(os.path.join(pathdir, "*.sr")) \
            + glob.glob(os.path.join(pathdir, "*.ras")) \
            + glob.glob(os.path.join(pathdir, "*.tiff")) \
            + glob.glob(os.path.join(pathdir, "*.tif"))

def addfiles(lstfile, dstdir):
    #funcsave = lambda name, bsvg: saveasfile(dstdir, name, bsvg)
    
    for path in lstfile:
        if os.path.isdir(path): # if folder
            addfiles(getreadableimgfile(path), dstdir)
        elif os.path.isfile(path):
            #convert image
            print("Processing {}:".format(path))
            img = cv2.imread(path)
            scanchars(img, dstdir)
        else:
            print("{}: File not found!".format(path))
        

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate SVG files from scanned image of a special form.')
    parser.add_argument('dest', metavar='destdir', 
                    help='output directory where SVG files will be stored')
    parser.add_argument('srcs', metavar='src', nargs='+',
                    help='images or directories that contains scanned images of a special form')

    args = parser.parse_args()

    addfiles(args.srcs, args.dest)
    
    