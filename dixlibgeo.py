#! /usr/bin/python

####################################################
# APRS digipeater and gateway for amateur radio use
#
# (C) HA5DI - 2012
#
# http://sites.google.com/site/dixprs/
####################################################

from math import *

########################################################################

def km2mi(v):
    return v * 0.621371192
    
def mi2km (v):
    return v / 0.621371192     

def fmtdist(v, mode):
    if mode:
        s = "%0.1f km" % (v) 
    else:
        s = "%0.1f mi" % (km2mi(v))
        
    return s        

def qra2geo(s):
    w = s.upper() 
    x = 20.0*(ord(w[0])-65) + 2.0*(ord(w[2])-48) + (ord(w[4])-65)/12.0 + 1.0/24.0 - 180.0
    y = 10.0*(ord(w[1])-65) + (ord(w[3])-48) + (ord(w[5])-65)/24.0 + 1.0/48.0 - 90.0
    return (x, y)

def deg2rad(x):
    return x * 3.141592765 / 180.0
    
def qradist(q1, q2):

    p1 = (deg2rad(q1[1]), deg2rad(q1[0]))
    p2 = (deg2rad(q2[1]), deg2rad(q2[0]))
    
    dlon = p2[0]-p1[0]
    dlat = p2[1]-p1[1]
    a = (sin(dlat/2.0))**2.0 + cos(p1[1]) * cos(p2[1]) * (sin(dlon/2.0))**2.0
    c = 2 * atan2(sqrt(a), sqrt(1.0-a))
    d = 6378 * c
    return d
    
