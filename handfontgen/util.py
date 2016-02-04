#!/usr/bin/env/python3
# coding: utf-8
# ちゃんとutf-8で開いてくれよ>エディター

import cv2
import subprocess
import sys
import shlex

def getgrayimage(image):
    # if image is not grayscale, convert to grayscale
    # this can cause error in some cases?
    if image.ndim == 2:
        grayscale = image
    else:
        grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return grayscale

def checkcygwin():
    try:
        p = subprocess.Popen(
            ['uname'],
            #stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False
            )
        stdout, stderr = p.communicate()
    except:
        # not posix
        return False
    
    if b'CYGWIN' in stdout: # running in Cygwin
        return True
    else:
        return False
    
# Windows python running in Cygwin sometimes gets 
# Cygwin /cygdrive/c/... path, which requires conversion
def cygwinconversionneeded():
    # Anaconda Python
    # sys.version: '3.5.1 |Anaconda 2.4.1 (64-bit)| (default, Jan 19 2016, 12:15:43) [MSC v.1900 64 bit (AMD64)]'
    # os.name: 'nt'
    # sys.platform: 'win32'
    # platform.system(): 'Windows'

    # Cygwin Python
    # os.name: 'posix'
    # sys.platform: 'cygwin'
    # platform.system(): 'CYGWIN_NT-6.1'
    
    try:
        p = subprocess.Popen(
            ['uname'],
            #stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False
            )
        stdout, stderr = p.communicate()
    except:
        # not posix
        return False
    
    if b'CYGWIN' in stdout: # running in Cygwin
        if sys.platform == 'cygwin': # Cygwin Python
            return False
        else: #'win32' -> Windows Python
            return True
    else:
        return False

# convert cygwin path into windows path
def cygpathconv(path):
    cmd = 'cygpath "{}"'.format(path)
    p = subprocess.Popen(
        shlex.split(cmd),
        #stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False
        )
    stdout, stderr = p.communicate()
    
    #if stderr:
    #    raise 
    #print(argpath, stdout, stderr)
    return stdout.decode('utf-8').strip()
    
def escapepath(path):
    #return path.replace("\\", "/")
    return path.replace("\\", "/")