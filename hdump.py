#! /usr/bin/python

####################################################
# APRS digipeater and gateway for amateur radio use
#
# (C) HA5DI - 2012
#
# http://sites.google.com/site/dixprs/
####################################################

def hdump(s):
    i =k = 0
    
    w1 = w2 = ''
    print
    
    for p in s:
        r = ord(p)
        w1 += '%02X ' % (r)
	
        if r<32 or r>127:
            w2 += '.'
        else:
            w2 += p
	
        i += 1
	
        if i==16:
            print '%04X' % (k), w1, w2
            w1 = w2 = ''
            i = 0
            k += 16
    if i<>0:
        print '%04X %-48s %s' % (k, w1, w2)

    return

