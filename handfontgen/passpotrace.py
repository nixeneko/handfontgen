#!/usr/bin/env/python3
# coding: utf-8
# ちゃんとutf-8で開いてくれよ>エディター

import numpy as np
import cv2
import subprocess

# potrace command
POTRACE = 'potrace'
    
def passpotrace(image, optionargs=[]): 
    # potrace supports only pnm (pbm, pgm, ppm), bmp
    # and cv2.imencode() supports all of them.
    
    # convert to bmp binary so that potrace can handle it
    retval, buf = cv2.imencode('.bmp', image)
    if retval == False:
        raise ValueError('The Given image could not be converted to BMP binary data')
    # convert buf from numpy.ndarray to bytes
    binbmp = buf.tostring()
    #optionargs = []
    
    args = [
        POTRACE,
        '-', '-o-', '--svg'
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
        binsvg = stdout
    else:
        raise RuntimeError('Potrace threw error:\n' + stderr.decode('utf-8'))
        
    return binsvg
    
def main():
    testpic = cv2.imread('resources/marker_50.png', cv2.IMREAD_GRAYSCALE)
    print(passpotrace(testpic).decode('utf-8'))

if __name__ == '__main__':
    main()