#!/usr/bin/env/python3
# coding: utf-8
# ちゃんとutf-8で開いてくれよ>エディター

import numpy as np
import cv2
import copy
import random

MARKER = cv2.imread('resources/marker_150.png', cv2.IMREAD_GRAYSCALE)
DOCSIZE = (191.7, 278.7)
dpi = 100 
dpm = dpi / 25.4
DOCPXLS = (int(DOCSIZE[0]*dpm),int(DOCSIZE[1]*dpm))


def getgrayimage(image):
    # if image is not grayscale, convert to grayscale
    # this can cause error in some cases?
    if image.ndim == 2:
        grayscale = image
    else:
        grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return grayscale
        
def getapproxmarkerradius(image):
    return int(min(image.shape[0:2]) * 0.03 /2)

def detectmarker(image):
    grayscale = getgrayimage(image)
    mkradius = getapproxmarkerradius(grayscale) # approximate marker radius
    marker = cv2.resize(MARKER, (mkradius*2, mkradius*2)) # resize the marker
    
    #template matching
    matched = cv2.matchTemplate(grayscale, marker, cv2.TM_CCORR_NORMED) #returns float32
        
    #detect 4 greatest values
    markerposarray = []
    for i in range(4):
        (minval, maxval, minloc, maxloc) = cv2.minMaxLoc(matched)
        markerposarray.append(tuple(map(lambda x: x+mkradius, maxloc))) 
        cv2.circle(matched, maxloc, mkradius, (0.0), -1) #ignore near the current minloc
        
    return markerposarray

def getmarkercenter(image, pos):
    mkradius = getapproxmarkerradius(image)
    buffer = int(mkradius * 0.15)
    roisize = mkradius + buffer # half of the height or width
    x = pos[0] - roisize
    y = pos[1] - roisize
    w = 2 * roisize
    h = 2 * roisize
    roi = image[y:y+h, x:x+w]
    
    grayroi = getgrayimage(roi)
    ret, binimage = cv2.threshold(grayroi,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    nlabels, labels, stats, centroids = cv2.connectedComponentsWithStats(binimage)
    # stats[0], centroids[0] are for the background label. ignore
    lblareas = stats[1:,cv2.CC_STAT_AREA]
    
    ave = np.average(centroids[1:], axis=0, weights=lblareas)
    return tuple(np.array([x, y]) + ave) # weighted average pos of centroids

def sortrectpoints(posarray):
    #print(posarray)
    # get a point which has smallest y
    p0 = min(posarray, key=lambda p:p[1])
    
    pts_angle = []
    posarraytmp = copy.copy(posarray)
    posarraytmp.remove(p0)
    for p in posarraytmp:
        dx = p[0] - p0[0]
        dy = p[1] - p0[1]
        angle = abs(dy)/(abs(dx)+abs(dy)) * 90
        pts_angle.append((angle, p))
        
    pts_angle_sorted = sorted(pts_angle, key=lambda x:x[0])
    pointclockwise = [p0]
    pointclockwise.extend([x[1] for x in pts_angle_sorted])
    #print(pointclockwise)
    
    # detect short sides
    lenarray = []
    for i in range(4):
        for j in range(i):
            lenarray.append(
                ((posarray[i],posarray[j]),
                 np.linalg.norm(np.array(posarray[i]) - np.array(posarray[j]))))
    sortedlen = sorted(lenarray, key=lambda x:x[1]) # sort by distance of 2 points
    # get array of tuple of points
    shortsides = [x[0] for x in sortedlen[0:2]]
    # longsides = [x[0] for x in sortedlen[2:4]]
    # diagonals = [x[0] for x in sotedlen[4:6]]
    
    # select a shortside of which midpoint has smaller y position
    def getmidpointy(parray): # y position of midpoint
        return (parray[0][1] + parray[1][1]) / 2
    s0y = getmidpointy(shortsides[0]) 
    s1y = getmidpointy(shortsides[1])
    shorttop = shortsides[0] if s0y <= s1y else shortsides[1]
    #print(s0y, s1y, shorttop)
    for i in range(4):
        if pointclockwise[i] in shorttop and pointclockwise[(i+1)%4] in shorttop:
            retpointlist = pointclockwise[i:] + pointclockwise[:i]
            break
    #print(retpointlist)
    return retpointlist
    
def transform(image, rectpoints):
    docrect = np.array([(0,0), (DOCPXLS[0], 0), (DOCPXLS[0], DOCPXLS[1]), (0, DOCPXLS[1])], 'float32')
    transmat = cv2.getPerspectiveTransform(np.array(rectpoints, 'float32'), docrect)
    return cv2.warpPerspective(image, transmat, DOCPXLS)

def correctslant(image):
    #mkradius = getapproxmarkerradius(testpic) # approximate marker radius
    matchedposarray = detectmarker(image)
    rectpoints = []
    for pos in matchedposarray:
        rectpoints.append(getmarkercenter(image, pos))
    rect = sortrectpoints(rectpoints)
    straightened = transform(image, rect)
    return straightened
    
def main():
    testpic = cv2.imread('resources/test1_300dpi.jpg')
    
    result = correctslant(testpic)
    
    cv2.imshow('result', result)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()