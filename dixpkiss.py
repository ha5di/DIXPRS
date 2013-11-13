#!/usr/bin/python

####################################################
# APRS digipeater and gateway for amateur radio use
#
# (C) HA5DI - 2012
#
# http://sites.google.com/site/dixprs/
####################################################

import serial
import dixpcommon
import dixdrvudp
import socket

def raw2kiss(raw):
    # Escape special characters to make it binary transparent

    # FESC
    w = raw.replace(chr(0xc0), chr(0xdb) + chr(0xdc))

    # FEND
    w = w.replace(chr(0xc0), chr(0xdb) + chr(0xdd))

    return w               
    
                                
def procmain(dev, (udptx, udpgw,udprx, udpcc), (kissport, speed, ctrl), ptt, debug, mycall):
        
    buf = ''
    wsc = False

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

    # Initialize serial port
     
    try:
        ser = serial.Serial(kissport, speed)
        ser.timeout = 0.01                                      

        # Initialize KISS TNC       

        for k, v in ctrl.iteritems():
            if k == 'TXD':
                ser.write(chr(0xc0) + chr(0x01) + raw2kiss(chr(v)) + chr(0xc0)) 

            elif k == 'PPERSIST':
                ser.write(chr(0xc0) + chr(0x02) + raw2kiss(chr(v)) + chr(0xc0))

            elif k == 'SLOTTIME':
                ser.write(chr(0xc0) + chr(0x03) + raw2kiss(chr(v)) + chr(0xc0))
                
            elif k == 'TXTAIL':
                ser.write(chr(0xc0) + chr(0x04) + raw2kiss(chr(v)) + chr(0xc0))
                
            elif k == 'DUPLEX':
                ser.write(chr(0xc0) + chr(0x05) + raw2kiss(chr(v)) + chr(0xc0))
                
    except serial.SerialException:
        ser = None
     
    # Main program loop    

    while True:
        try:
            # Read serial line
            if ser <> None:
                try:
                    s = ser.read(1000)
                except:
                    pass
                                                            
                try:
                    n = len(s)
                except TypeError:
                    n = 0
                
            else:
                n = 0                
            
            # Process received data
            
            if n <> 0:
                lst = []
                
                w = s.split(chr(0xc0))
                n = len(w)
                
                # No 0xc0 in frame
                if n == 1:
                    buf += w[0]
            
                # Single 0xc0 in frame
                elif n == 2:
                    # Closing 0xc0 found
                    if w[0] <> '':
                        # Partial frame continued, otherwise drop
                        lst.append(buf + w[0])
                        buf = ''
            
                    # Opening 0xc0 found
                    else:
                        lst.append(buf)
                        buf = w[1]
            
                # At least one complete frane received
                elif n >= 3:
                    
                    for i in range(0, n - 1):
                        st = buf + w[i]
            
                        if st <> '':
                            lst.append(st)
                            buf = ''
            
                    if w[n - 1] <> '':
                        buf = w[n - 1]                

                # Loop through received frames
                for p in lst:
                    if len(p) == 0:
                        continue
                        
                    if ord(p[0]) == 0:
                        txt = dixpcommon.raw2txt(p[1:])
                        #print "KISS RAW2TXT:", txt
                        #print "========================================="

                        if txt <> '':                             
                            st = "R" + dev + "0" + txt # Single channel device
                            
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
                                    
                    # Control frame received
                    else:
                        pass


            else:
                # No KISS data received, do lower priority jobs
                if socrx <> None:
                    s = socrx.receive()
                    
                    if s <> None:
                        #print "KISS:", s
                        
                        # Data to send
                        if s[0] == 'D':
                            raw = dixpcommon.txt2raw(s[1:])

                            if ser <> None:
                                try:
                                    if ptt:
                                        ser.write(chr(0xc0) + chr(0x00) + raw2kiss(raw) + chr(0xc0))

                                        if soccc <> []:
                                            stcc = "DIXPRS2201|" + mycall + "|T" + dev + "|" + s[1:] 
                
                                            for i in range(0, len(soccc)):
                                                try:
                                                    soccc[i].sendto(stcc, (udpcc[i][0], udpcc[i][1]))
                                                except (socket.error, socket.gaierror):
                                                    pass                                        

                                except:
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
