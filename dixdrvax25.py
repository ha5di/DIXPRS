#! /usr/bin/python

####################################################
# APRS digipeater and gateway for amateur radio use
#
# (C) HA5DI - 2012
#
# http://sites.google.com/site/dixprs/
####################################################

def AX25CallEncode(cal):

    if len(cal) <> 3:
        return ''
    
    w = cal[0].split('-')

    if len(w) < 1 or len(w) > 2:
        return ''

    if len(w[0]) < 1 or len(w[0]) > 6:
        return ''
    
    if len(w) == 1:
        ssid = 0
    else:
        ssid = int(w[1])
    
    s = ''
    
    for p in w[0]:
        s += chr(ord(p) << 1)

    while len(s) < 6:
        s += chr(0x40)
        
    ct = (ssid << 1) | 0x60

    if cal[1] <> 0:
        ct |= 0x01

    if cal[2] <> 0:
        ct |= 0x80
        
    return s + chr(ct)

####################################################

def AX25UIRawAssemble(frm):
    if len(frm) <> 4:
        return ''
    
    s = AX25CallEncode([frm[1], 0, 0])

    if len(frm[2]) == 0:
        s += AX25CallEncode([frm[0], 1, 0])

    else:
        s += AX25CallEncode([frm[0], 0, 0])

        for i in range(0, len(frm[2])):
            if i <> len(frm[2]) - 1:
                s += AX25CallEncode([frm[2][i][0], 0, frm[2][i][1]])

            else:
                s += AX25CallEncode([frm[2][i][0], 1, frm[2][i][1]])

        return s + chr(0x03) + chr (0xf0) + str(frm[3])
