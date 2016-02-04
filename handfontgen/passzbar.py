#!/usr/bin/env/python3
# coding: utf-8
# ちゃんとutf-8で開いてくれよ>エディター

import numpy as np
import cv2
import subprocess

# zbar command
ZBARIMG = 'zbarimg'

DPMM300DPI = 300/25.4

def passzbar(image): 
    # convert to bmp binary so that zbar can handle it
    retval, buf = cv2.imencode('.bmp', image)
    if retval == False:
        raise ValueError('The Given image could not be converted to BMP binary data')
    # convert buf from numpy.ndarray to bytes
    binbmp = buf.tobytes()
    optionargs = []
    
    args = [
        ZBARIMG,
        ':-', '-q'
    ] + optionargs
    
    p = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False
        )
        
    stdout, stderr = p.communicate(input=binbmp)
    if len(stderr) == 0:
        bindata = stdout
    else:
        raise RuntimeError('ZBar threw error:\n' + stderr.decode('utf-8'))
    
    t = bindata.split(b":", 1)
    #print(t)
    type = None
    data = None
    if len(t) == 2:
        type, data = t
    return type, data
    
def main():
    testpic = cv2.imread('canvas.png', cv2.IMREAD_GRAYSCALE)
    bartype, bardata = passzbar(testpic)
    print(bardata.decode('utf-8'))

if __name__ == '__main__':
    main()