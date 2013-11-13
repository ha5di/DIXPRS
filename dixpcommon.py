#!/usr/bin/python 

####################################################
# APRS digipeater and gateway for amateur radio use
#
# (C) HA5DI - 2012
#
# http://sites.google.com/site/dixprs/
####################################################

import time
import hashlib
import Queue
import socket
import multiprocessing
import sqlite3

import dixdrvudp
import dixpkiss
import dixpagwpe
import dixpax25
import dixlibax25

import hdump

from dixlibcommon import *
	
class RADIOPORT():
    def __init__ (self):
        self.prtid = '?'                    # Port ID
        self.hwtyp = None                   # Hw interface type
        self.hwcfg = None                   # Hw setup parameters
        self.udptx = None                   # UDP port to send command/data to driver process 
        self.udpmn = None                   # UDP port to send data to main program
        self.udpgw = None                   # UDP port to send data to Internet Gateway
        self.udpcc = []                     # List of servers to send UDP CC
        self.soctx = None                   # UDP socket to send command/data to driver process
        self.txdup = {}                     # Dictionary to store guarded MD5 values with their time
        self.rxdtq = Queue.Queue()          # Queue for received frames        
        self.txdtq = Queue.Queue()          # Queue for sent frames (those really sent out in air)
        self.txddi = Queue.Queue()          # Queue for sent frames (those really sent out in air)
        self.txdgw = Queue.Queue()          # Queue for sent frames (those really sent out in air)        
        self.axcal = ''                     # AX.25 sorce call 
        self.axdst = ''                     # AX.25 destination
        self.axvia = ''                     # AX.25 via
        self.drvpr = None                   # Driver process associated to port
        self.bcntx = None                   # Beacon text
        self.blkls = []                     # Blacklistl
        self.widen = []                     # List of WideN digis we are repeating
        self.phgbc = ''                     # PHG string
        self.rngbc = 0                      # Range value
        self.pdesc = ''                     # Port description
        #self.chanr = 0                      # Channel number
        self.debug = 0
        self.ptton = False                  # 
        self.gsloc = False                  # Gate sent traffic to IGATE
        self.gsdig = False                  # Gate sent traffic to IGATE
        self.digen = True                   # Enable digipeater
        self.gtnws = False                  # Gate NWS WX bulletins to Rf (US)
        self.gtbom = False                  # Gate BOM WX bulletins to Rf (Australia)

        self.tsgtq = Queue.Queue()          # Outgoing gated packet queue
        self.tsgtm = False                  # Threshold watching mode
        self.tsgtd = 0                      # Delay time set
        
        self.tsglh = 0.75                   # Threshold high
        self.tsgll = 0.5                    # thershold low
        self.tsgid = 5.0                    # Delay start dequing, seconds
        self.aispp = 1200.0                 # Modem baudrate (on air) bit/s
                
        return
        
    
    def start(self):
        self.dbcon = sqlite3.connect(':memory:')
        self.dbcur = self.dbcon.cursor()
        
        self.dbcur.execute('''CREATE TABLE traffic (tm real, ln integer, rxtx integer)''')    
        self.dbcon.commit()
     
        if self.udptx <> None:
            try:
                self.soctx = dixdrvudp.UDPTx(self.udptx)

            except socket.error:
                pass        
                
        if self.hwtyp == 'KISS':
            self.drvpr = multiprocessing.Process(target=dixpkiss.procmain, args=(self.prtid, (self.udpmn, \
            self.udpgw, self.udptx, self.udpcc), (self.hwcfg[0], self.hwcfg[1], self.hwcfg[2]), \
            self.ptton, self.debug, cvars.get('genCFGcall')))                            

            self.drvpr.start()
            
        elif self.hwtyp == 'AGWPE':
            self.drvpr = multiprocessing.Process(target=dixpagwpe.procmain, args=(self.prtid, (self.udpmn, \
            self.udpgw, self.udptx, self.udpcc), (self.hwcfg[0], self.hwcfg[1], self.hwcfg[2], self.hwcfg[3]), \
            self.ptton, self.debug, cvars.get('genCFGcall')))       

            self.drvpr.start()
            
        elif self.hwtyp == "AX25":
            self.drvpr = multiprocessing.Process(target=dixpax25.procmain, args=(self.prtid, (self.udpmn, \
            self.udpgw, self.udptx, self.udpcc), (self.hwcfg[0], self.hwcfg[1]), self.ptton, self.debug, cvars.get('genCFGcall')))                            
            
            self.drvpr.start()
                                
        return
                
            
    def stop(self):
        self.dbcur.close()
        self.dbcon.close()
        
        if self.soctx <> None:
            try:
                self.soctx.close()
            except socket.error:
                pass
                
        if self.drvpr <> None:
            self.drvpr.terminate()         
            
        return                       
    
    
    def sendchkdup(self, s):     
        #print "000", s
        
        status = 0
        
        if self.soctx == None:
            return status
            
        #print "111", s                    
        # Clean up MD5 cache
        
        w = {}
        t = time.time() - 30.0              # 60 seconds guard time
          
        for k, v in self.txdup.iteritems():
            if v > t:
                w[k] = v
                
        self.txdup = w
        
        # Calculate MD5 for current frame
        
        m = hashlib.md5()     
        
        try:
            # Add source callsign with SSID
            m.update(s.split('>')[0])
            #print "DUP SOURCE:", s.split('>')[0]
            
            # Add destination callsign without SSID     
            m.update(s[:s.find(':')].split(',')[0].split('>')[1].split('-')[0])
            #print "DUP DESTINATION:", s[:s.find(':')].split(',')[0].split('>')[1].split('-')[0]
            
            # Add info field
            m.update(s[s.find(':') + 1:])
            #print "DUP INFO:", s[s.find(':') + 1:]
            
            d = m.digest()
            #print "DUP TIME:", time.time()
        
            try:
                self.txdup[d]
                #print "DUP YES", self.txdup[d]
            except KeyError:
                #print "DUP NO"
                
                self.txdup[d] = time.time()

                if self.soctx <> None:
                    try:
                        #print "+++", s
                        self.soctx.send('D' + s)
                        
                        self.dbcur.execute("INSERT INTO traffic VALUES(%f, %d, %d)" % (time.time(), len(s), 1))
                        self.dbcon.commit()
                        status = 1
 
                    except socket.error:                 
                        pass
                                
        except IndexError:
            pass
            
        return status
        
    def send(self, s):
        if self.sendchkdup(s) <> 0:
            self.txdtq.put(s)
        
        return
        

    def senddigi(self, s):
        if self.sendchkdup(s) <> 0:
            self.txddi.put(s)
        
        return
            
    def sendmy(self, s):
        if self.axdst <> '':
            if self.axvia == '':
                txt = self.axcal + '>' + self.axdst + ':' + s
            else:
                txt = self.axcal + '>' + self.axdst + ',' + self.axvia + ':' + s

            if self.sendchkdup(txt) <> 0:
                self.txdtq.put(txt)
        
        return
         
    def sendgatenoq(self, s):
        if self.axdst <> '':
            if self.axvia == '':
                txt = self.axcal + '>' + self.axdst + ':' + s
            else:
                txt = self.axcal + '>' + self.axdst + ',' + self.axvia + ':' + s
 
            if self.sendchkdup(txt) <> 0:
                self.txdgw.put(txt)
        
        return
 
    def sendgate(self, s):
        if self.tsgtq.empty():
            load = self.trload()
        
            if load[0] + load[1] > 0.75:
                self.tsgtq.put(s)
                self.tsgtm = True
            else:
                self.sendgatenoq(s)        
                
        else:               
            self.tsgtq.put(s)
            self.tsgtm = True
                
        return
        
        
    def dequeuegate(self):      
        if self.tsgtq.empty():
            self.tsgtm = False
            
        else:
            l = self.trload()
            load = l[0] + l[1]
            #print "000", self.tsgtm, load          
            
            if self.tsgtd == 0:
                #print "111", self.tsgtm, load
                l = self.trload()
                load = l[0] + l[1]
                
                
                if self.tsgtm:                    
                    #print "222", self.tsgtm, load
                    if load < self.tsgll:
                        #print "333", self.tsgtm, load
                        self.tsgtm = False 
                        self.tsgtd = time.time() + self.tsgid
                else:
                    while 1:
                        #print "444", self.tsgtm, load
                        l = self.trload()
                        load = l[0] + l[1]
                        
                        if load < self.tsglh:
                            #print "555", self.tsgtm, load
                            self.sendgatenoq(self.tsgtq.get())
                            
                            if self.tsgtq.empty():
                                #print "666", self.tsgtm, load
                                break
                        else:
                            #print "777", self.tsgtm, load
                            self.tsgtm = True
                            break                                  
            else:
                #print "888", self.tsgtm, load
                
                if time.time() >= self.tsgtd:
                    #print "999", self.tsgtm, load
                    self.tsgtd = 0
                    
        return  

 
    def rxenqueue(self, s):
        if len(s) > 1:
            if s[0] == 'R':
                self.rxdtq.put(s[1:])
            
        return
    
    
    def receive(self):
        try:
            s = self.rxdtq.get(block = False)

            self.dbcur.execute("INSERT INTO traffic VALUES(%f, %d, %d)" % (time.time(), len(s), 0))
            self.dbcon.commit()

        except Queue.Empty:
            s = ''
            
        return s
    

    def sent(self):
        try:
            s = self.txdtq.get(block = False)
        except Queue.Empty:
            s = ''
            
        return s
                             

    def sentdigi(self):
        try:
            s = self.txddi.get(block = False)
        except Queue.Empty:
            s = ''
            
        return s


    def sentgate(self):
        try:
            s = self.txdgw.get(block = False)
        except Queue.Empty:
            s = ''
            
        return s
          
          
    def dbclean(self):
        self.dbcur.execute("DELETE FROM traffic WHERE tm<=%f" % (time.time() - 30.0))
        self.dbcon.commit()
        return  
        
    def trload(self):
        self.dbcur.execute("SELECT sum(ln) FROM traffic WHERE tm>%f AND rxtx=0" % (time.time() - 30.0))
        res0 = self.dbcur.fetchone()
        
        if res0[0] == None:
            r0 = 0
        else:
            r0 = res0[0]

        self.dbcur.execute("SELECT sum(ln) FROM traffic WHERE tm>%f AND rxtx=1" % (time.time() - 30.0))
        res1 = self.dbcur.fetchone()
        
        if res1[0] == None:
            r1 = 0
        else:
            r1 = res1[0]
                     
        cf = self.aispp / 8.0 * 30  # Byte throughput in 30 secs                          
        return (r0 / cf, r1 / cf)               

def txt2raw(s):
    ix = s.find(':')
     
    if ix < 0:
        return None
        
    hdr = s[:ix]
    inf = s[ix + 1:]
    
    w1 = hdr.split('>')
    callfm = w1[0]
    
    w2 = w1[1].split(',')
    callto = w2[0]

    r = kk2(callto) + kk2(callfm)
    
    for i in range(1, len(w2)):
        if len(w2[i]) > 1:
            r += kk2(w2[i])

    rr = r[:-1] + chr(ord(r[-1]) | 0x01) + chr(0x03) + chr(0xf0) + inf
    return rr
                        
    
def kk2(ctxt):
    if ctxt[-1] == '*':
        s = ctxt[:-1]
        digi = True
    else:
        s = ctxt
        digi = False
                
    ssid = 0
    w1 = s.split('-')    

    call = w1[0]
    
    while len(call) < 6:
        call += ' '
        
    r = ''
    
    for p in call:
        r += chr(ord(p) << 1)        
    
    if len(w1) <> 1:
        try:
            ssid = int(w1[1])
        except ValueError:
            return ''
        
    ct = (ssid << 1) | 0x60

    if digi:
        ct |= 0x80
    
    return r + chr(ct)

     
def raw2txt(raw):
    #hdump.hdump(raw)
    
    # Is it too short?
    if len(raw) < 16:
        #print "&&& 1"
        #hdump.hdump(raw)
        return ''
        
    r1 = ''

    for i in range(0, len(raw)):
        if ord(raw[i]) & 0x01:
            break
    
    # Is address field length correct?        
    if (i + 1) % 7 <> 0:
        #print "&&& 2"
        return ''
                            
    
    n = (i + 1) / 7
    
    # Less than 2 callsigns?
    if n < 2 or n > 10:
        #print "&&& 3"
        return ''
        
    try:
        if (i + 1) % 7 == 0 and n >= 2 and ord(raw[i + 1]) & 0x03 == 0x03 and ord(raw[i + 2]) == 0xf0:
            strinfo = raw[i + 3:]
            
            if len(strinfo) <> 0:
                strto = hh1(raw) 

                if strto == '':
                    #print "&&& 4", strto
                    return ''
                             
                strfrom = hh1(raw[7:])

                if strfrom == '':
                    return ''
                    
                if dixlibax25.IsInvalidCall(strfrom):
                    #print "&&& 5"
                    return ''
                                    
                r1 = strfrom + '>' + strto
                
                for i in range(2, n):
                    s = hh1(raw[i * 7:])
                    
                    if s == '':
                        #print "&&& 6"
                        #hdump.hdump(raw)
                        return ''
                        
                    r1 += ',' + s
                    
                    if ord(raw[i * 7 + 6]) & 0x80:
                        r1 += '*'
                        
                r1 += ':' + strinfo
    
    except IndexError:
        #print "&&& X"
        #hdump.hdump(raw)
        pass

    return r1
    

def hh1(rawcall):
    s = ''
    
    for i in range(0, 6):
        ch = chr(ord(rawcall[i]) >> 1)
        
        if ch == ' ':
            break
            
        s += ch
                                    
    ssid = (ord(rawcall[6]) >> 1) & 0x0f
    
    
    if s.isalnum() == False:
    	  return ''
        		
    
    if ssid > 0:            
        s += "-%d" % (ssid)

    return s     
    
    
radioports = []    
    
