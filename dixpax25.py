#!/usr/bin/python

####################################################
# APRS digipeater and gateway for amateur radio use
#
# (C) HA5DI - 2012
#
# http://sites.google.com/site/dixprs/
####################################################

import time
import dixpcommon
import dixdrvudp
import socket

try:
    import _ax25
except ImportError:
    pass    

def b2a(s):
    w = ''

    for p in s:
        w += chr(((ord(p) & 0xf0) >> 4) | 0x40)
        w += chr((ord(p) & 0x0f) | 0x40)

    return w            
    
                                
def procmain(dev, (udptx, udpgw,udprx, udpcc), (axdev, ctrl), ptt, debug, mycall):
    
    # Open UDP ports
    
    socgw = None
    socrx = None
    soctx = None
    soccc = []
        
    if udpgw <> 0:
        socgw = dixdrvudp.UDPTx(udpgw)
        socgw.settimeout(0.01)
       
    if udprx <> 0:
        socrx = dixdrvudp.UDPRx(udprx)
        socrx.settimeout(0.01)
        
    if udptx <> 0:
        soctx = dixdrvudp.UDPTx(udptx)
        soctx.settimeout(0.01)
    
    for i in range(0, len(udpcc)):
        soccc.append(socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
        soccc[i].settimeout(0.1)
        
    # Initialize AX25 port
    
    soc = _ax25.RawSocket()

    for k, v in ctrl.iteritems():
        if k == 'TXD':
            _ax25.RawTx(soc, b2a(chr(0x01) + chr(v)), 2, axdev)

        elif k == 'PPERSIST':
            _ax25.RawTx(soc, b2a(chr(0x02) + chr(v)), 2, axdev)

            
        elif k == 'SLOTTIME':
             _ax25.RawTx(soc, b2a(chr(0x03) + chr(v)), 2, axdev)
            
        elif k == 'TXTAIL':
             _ax25.RawTx(soc, b2a(chr(0x04) + chr(v)), 2, axdev)
            
        elif k == 'DUPLEX':
             _ax25.RawTx(soc, b2a(chr(0x05) + chr(v)), 2, axdev)

    # Main program loop    
    
    while True:
        try:        
            r = _ax25.RawRx(soc)            

            if r[0][1] == axdev:

                if r[1][0] == chr(0x00):
                    txt = dixpcommon.raw2txt(r[1][1:])
                                    
                    if txt <> '':
                        st = "R" + dev + "0" + txt # Single channel device
                        
                        if soccc <> []:
                            stcc = "DIXPRS2201|" + mycall + "|" + st[:2] + "|" + st[3:]
                            
                        # Send it to GW 
 
                        if socgw <> None:
                            socgw.send(st)
                            
                                 
                        # Send it to main program
                        if soctx <> None:
                            soctx.send(st)                                                          

                        if soccc <> []:
                            stcc = "DIXPRS2201|" + mycall + "|" + st[:2] + "|" + st[3:]
                            
                            for i in range(0, len(soccc)):
                                try:
                                    soccc[i].sendto(stcc, (udpcc[i][0], udpcc[i][1]))
                                except (socket.error, socket.gaierror):
                                    pass
                                                        
            else:
                # No data received, do lower priority jobs
                if socrx <> None:
                    s = socrx.receive()
                    
                    if s <> None:
                        # Data to send
                        if s[0] == 'D':
                            raw = dixpcommon.txt2raw(s[1:])
                            w = b2a(chr(0) + raw)
                            
                            if ptt:
                                _ax25.RawTx(soc, w, len(w), axdev)        

                                if soccc <> []:
                                    stcc = "DIXPRS2201|" + mycall + "|T" + dev + "|" + s[1:] 
        
                                    for i in range(0, len(soccc)):
                                        try:
                                            soccc[i].sendto(stcc, (udpcc[i][0], udpcc[i][1]))
                                        except (socket.error, socket.gaierror):
                                            pass                                        
                                                                                                                         
        except KeyboardInterrupt:
            pass 
		
    # Shutting down
    if socgw <> None:
        socgw.close()
        
    if socrx <> None:
        socrx.close()
    
    if soctx <> None:
        soctx.close()

	
