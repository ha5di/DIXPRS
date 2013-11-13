#! /usr/bin/python

####################################################
# APRS digipeater and gateway for amateur radio use
#
# (C) HA5DI - 2012
#
# http://sites.google.com/site/dixprs/
####################################################

import  socket
import  time
import  hashlib
import  math

import  dixdrvudp
import  dixlibax25
import  dixprscommon
import  dixlibsql

from dixpcommon import radioports

from dixlibcommon import *


###############################################################################
###############################################################################

def mkcaptxt(port):   
    s = "MSG_CNT=%d,LOC_CNT=%d,DIR_CNT=%d,RF_CNT=%d,RFPORT_ID=" % (dixlibsql.getgatedmsgcount(port), dixlibsql.GetRfCntLoc(port), \
    dixlibsql.GetRfCntDir(port), dixlibsql.GetRfCntAll(port))
    
    if port < 0:
        s += "all"
    else:
        s += "%d" % (port)
                        
    return s 
    
    
def IsPosition(frm):   
    if len(frm) < 4:
        return False

    if len(frm[3]) == 0:
        return False
    
    dti = frm[3][0]

    return "$!/=@'`".find(dti) >= 0

###############################################################################
###############################################################################

def GetPosition(frm):
    dti = frm[3][0]

    if dti == "$":
        return nmea2geo(frm[3])
    
    elif dti == "'" or dti == "`":
        return posmice2geo(frm[1], frm[3])
            
    else:
        try:
            s1 = ''
            k = 0
            
            if dti == "!" or dti == "=":
                k = 1
        
            elif dti == "/" or dti == "@":
                k = 8
                    
            if k <> 0:
                if frm[3][k].isdigit():
                    return posaprs2geo(frm[3][k:k+8], frm[3][k+9:k+18])
                    
                else:
                    return poscomp2geo(frm[3][k+1:k+9])
        except:
            pass
        
    return (0,0)

###############################################################################
# Convert geographical position from APRS text to geographical format
#
# Input:        (latitude, longitude) in APRS text
# 
# Return:       geo - (latitude, longitude) in floating point degrees
#                      where N/E is positive
#
#                     or () in case of error
############################################################################### 

def posmice2geo(dst, inf):
    d = dst.split('-')[0]

    if len(d) <> 6:
        return (0, 0)
        
    if len(inf) < 9:
        return (0, 0)
                
    t1 = "0123456789ABCDEFGHIJKLPQRSTUVWXYZ"
    t2 = "01234567890123456789  0123456789 "
    
    s = ''
            
    for p in d:
        k = t1.find(p)
        
        if k < 0:
            return (0, 0)
        
        s += t2[k]
    
    try:
        lat = float(s[0:2])
    except ValueError:
        return (0, 0)

    try:
        latmmhh = float(s[2:4] + '.' + s[4:])
    except ValueError:
        return (0, 0)

    if latmmhh >= 60.0:
        return (0, 0)

    lat += latmmhh / 60.0
    
    if dst[3].isdigit() or dst[3] == 'L':
        lat = -lat
        
    d28 = ord(inf[1])
    
    if "PQRSTUVWXYZ".find(dst[4]) >= 0:
        lngoffset = 100
    else:
        lngoffset = 0

    lng = 0
    
    mm = ord(inf[2]) - 28
    
    if mm >= 60:
        mm -= 60
        
    mm += (ord(inf[3]) - 28.0) / 100.0

    lng += mm / 60.0    

    if "PQRSTUVWXYZ".find(dst[5]) >= 0:
        longdir = -1
    else:
        longdir = 1

    if d28 <= 127 and d28 >= 118 and lngoffset == 100:
        longdeg = d28 - 118
    elif d28 <= 127 and d28 >= 28 and lngoffset == 0:
        longdeg = d28 - 28
    elif d28 <= 117 and d28 >= 108 and lngoffset == 100:
        longdeg = d28 - 8
    else:
        longdeg = d28 + 72

    lng += longdeg
    lng *= longdir
    
    lat = int(lat * 100000) / 100000.0
    lng = int(lng * 100000) / 100000.0
    
    return (lat, lng)
    


def nmea2geo(inf):    
    w = inf.split(',')

    if w[0] == '$GPGGA':
        if len(w) < 6:
            return (0, 0)

        xlatval = w[2]
        xlatdir = w[3]
        xlngval = w[4]
        xlngdir = w[5]

    elif w[0] == '$GPGLL':      
        if len(w) < 5:
            return (0, 0)

        xlatval = w[1]
        xlatdir = w[2]
        xlngval = w[3]
        xlngdir = w[4]

    elif w[0] == '$GPRMC':      
        if len(w) < 7:
            return (0, 0)

        xlatval = w[3]
        xlatdir = w[4]
        xlngval = w[5]
        xlngdir = w[6]

    else:
        return (0, 0)

    try:
        lng = float(xlngval[:3])
    except ValueError:
        return (0, 0)

    try:
        lng += float(xlngval[3:]) / 60.0
    except ValueError:
        return (0, 0)
    
    try:
        lat = float(xlatval[:2])
    except ValueError:
        return (0, 0)

    try:
        lat += float(xlatval[2:]) / 60.0
    except ValueError:
        pr
        return (0, 0)

    if xlngdir == 'W':
        lng = -lng

    if xlatdir == 'S':
        lat = -lat
    
    return (lat, lng)

###############################################################################
# Convert geographical position from APRS text to geographical format
#
# Input:        (latitude, longitude) in APRS text
# 
# Return:       geo - (latitude, longitude) in floating point degrees
#                     where N/E is positive
#
#                     or () in case of error
############################################################################### 

def posaprs2geo(aprslat, aprslng):
    if len(aprslat) <> 8 or len(aprslng) <> 9:
        return (0, 0)

    if aprslat[4] <> '.' or aprslng[5] <> '.':
        return (0, 0)
        
    if not (aprslat[-1] == 'N' or aprslat [-1] == 'S'):
        return (0, 0)

    if not (aprslng[-1] == 'E' or aprslng [-1] == 'W'):
        return (0, 0)
        
    try:        
        lat = float(aprslat[0:2]) + float(aprslat[2:7]) / 60.0
    except ValueError:
        return (0, 0)
        
    if aprslat[-1] == 'S':
        lat = -lat
        
    try:
        lng = float(aprslng[0:3]) + float(aprslng[3:8]) / 60.0
    except ValueError:
        return (0, 0)
        
    if aprslng[-1] == 'W':
        lng = -lng

    lat = int(lat * 100000) / 100000.0
    lng = int(lng * 100000) / 100000.0
    
    return (lat, lng)

###############################################################################
# Convert geographical position from APRS compressed to geographical format
#
# Input:        cmp in APRS compressed
# 
# Return:       geo - (latitude, longitude) in floating point degrees
#                     where N/E is positive                                              
#
#                     or () in case of error
############################################################################### 

def poscomp2geo(cmp):
    
    if len(cmp) <> 8:
        return (0, 0)
        
    lat = 0
    lng = 0
        
    for p in cmp[:4]:
        ch = ord(p) - 33
        
        if ch < 0 or ch > 90:
            return (0, 0)
                
        lat = lat * 91.0 + ch
        
    lat = 90.0 - lat / 380926.0
    
    for p in cmp[4:]:
        ch = ord(p) - 33
        
        if ch < 0 or ch > 90:
            return (0, 0)

        lng = lng * 91.0 + ch
        
    lng = -180.0 + lng / 190463.0

    lat = int(lat * 100000) / 100000.0
    lng = int(lng * 100000) / 100000.0
    
    return (lat, lng)


###############################################################################
# Creates position report string
#
# Input:        
# 
# Return:       
#
############################################################################### 


def MkPosRep(port, txt):
    rcomp = True
    
    for p in radioports:
        if p.phgbc <> '':
            rcomp = False
    
    if rcomp:
        # Compressed position report
        w = posgeo2comp((cvars.get('genCFGlati'), cvars.get('genCFGlong')))
        s = '=' + cvars.get('genCFGsymb')[0] + w + cvars.get('genCFGsymb')[1]

        pr = ' sT'
        
        if port >= 0:
            rng = radioports[port].rngbc

            if rng > 0:

                # rng in miles
                rng = rng * 0.6213712
                ch = chr(int(math.log(rng / 2.0, 1.08) + 0.5) + 33)
                pr = '{' + ch + '!'

        s += pr                
        
    else:        
        # Plain position report with PHG
        w = posgeo2aprs((cvars.get('genCFGlati'), cvars.get('genCFGlong')))
        s = '=' + w[0] + cvars.get('genCFGsymb')[0] + w[1] + cvars.get('genCFGsymb')[1]
        s += 'PHG' + radioports[port].phgbc
        
    asl = cvars.get('genCFGasl')

    if asl > -9999.9:
        s += "/A=%06d" % (asl * 3.28084)
    
    s += txt.replace('%v', dixprscommon.version)

    return s

class IGPORT():

    def __init__(self, port):
        self.soctx = None
        self.rxdtq = Queue.Queue()
        self.txdtq = Queue.Queue()
        self.evntq = Queue.Queue()
        self.bcntx = None
        self.axhdr = None
        self.srvid = ''
        self.srvpr = 0
        self.srvfl = ''
        self.connr = 0
        
        
        try:
            self.soctx = dixdrvudp.UDPTx(port)
            self.soctx.settimeout(0.001)
        except socket.error:
            self.soctx = None
        
        return

    def close(self):
        if self.soctx <> None:
            try:
                self.soctx.close()
            except socket.error:
                pass
            
        return

    def send(self, s):
        if self.soctx <> None:
            try:
                self.soctx.send('D' + s)
                self.txdtq.put(s)
            except socket.error:
                pass

        return

   
    def sendmy(self, s):
        self.send(self.axhdr + ':' + s)

        return
    
    def receive(self):
        try:
            s = self.rxdtq.get(block=False)
        except Queue.Empty:
            s = ''

        return s

    def sent(self):
        try:
            s = self.txdtq.get(block=False)
        except Queue.Empty:
            s = ''

        return s    

    def putudpraw(self, s):
        if len(s) > 0:
            if s[0] == 'R':
                self.rxdtq.put(s[1:])

#            elif s[0] == 'S':
                
        return

###############################################################################	
    

###############################################################################
# Convert geographical position to APRS text format
#
# Input:	geo - (latitude, longitude) in floating point degrees
#                                           N/E is positive                                              
#
# Return:	(latitude, longitude) in APRS text 
###############################################################################	

def posgeo2aprs(geo):

    lng = abs(int(geo[0]))
    lat = abs(int(geo[1]))
    ln1 = (abs(geo[0]) - lng) * 60
    la1 = (abs(geo[1]) - lat) * 60
    
    w = '%d' % (lng)
    l1 = (2 - len(w))*'0' + w
    w = '%.02f' % (ln1)
    l2 = (5 - len(w))*'0' + w
    s1 = l1 + l2
    
    w = '%d' % (lat)
    l1 = (3 - len(w))*'0' + w
    w = '%.02f' % (la1)
    l2 = (5 - len(w))*'0' + w
    s2 = l1 + l2
    
    if geo[0] < 0:
        s1 += 'S'
    else: 
        s1 += 'N'
        
    if geo[1] < 0:
        s2 += 'W'
    else:
        s2 += 'E'
                                
    return (s1, s2)
    

###############################################################################
# Convert geographical position to APRS compressed format
#
# Input:	geo - (latitude, longitude) in floating point degrees
#                                           N/E is positive                                              
#
# Return:	(pos) in APRS compressed text 
###############################################################################	

def posgeo2comp(geo):

    lat = int(380926 * (90.0 - geo[0]))
    lng = int(190463 * (180.0 + geo[1]))
    
    la1 = lat / (91*91*91)
    wrm = lat % (91*91*91)
    
    la2 = wrm / (91*91)
    wrm = wrm % (91*91)
    
    la3 = wrm / 91
    la4 = wrm % 91
    
    ln1 = lng / (91*91*91)
    wrm = lng % (91*91*91)
    
    ln2 = wrm / (91*91)
    wrm = wrm % (91*91)
    
    ln3 = wrm / 91
    ln4 = wrm % 91

    s = chr(la1 + 33) + chr(la2 + 33) + chr(la3 + 33) + chr(la4 + 33)
    s += chr(ln1 + 33) + chr(ln2 + 33) + chr(ln3 + 33) + chr(ln4 + 33)

    return s

def StatusUpdate(s):
    cvars.put('genCFGstat', s)
    return

def StatusSend():
    r = False
    s = '>' + cvars.get('genCFGstat')

    igtport = cvars.get('igtport')
    
    if igtport <> None:
        if igtport.sendmy(s):
            r = True

    for p in radioports:
        p.sendmy(s)
        
    return r
    
