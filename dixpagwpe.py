#! /usr/bin/python

####################################################
# APRS digipeater and gateway for amateur radio use
#
# (C) HA5DI - 2012
#
# http://sites.google.com/site/dixprs/
####################################################

import  time
import  socket
import	Queue

import  dixdrvudp
import  dixdrvax25
import  dixpcommon

import  hdump
        
###############################################################################	
###############################################################################	

class AGWPECON:
    def __init__(self):
        self.phase = -1
        self.sockt = None
        self.servr = None
        self.prtnr = None
        self.tmdis = None
        self.recon = True
        self.rxque = Queue.Queue()
        self.dstid = None
        self.chanr = 0

        return
    
    def stop(self):
        if self.sockt <> None:
            try:
                self.sockt.close()

            except socket.error, s:
                pass
            
        return

    def receive(self):
        try:
            ax = self.rxque.get(False)
        except Queue.Empty:
            return None

        return ax
  
    def send(self, frm):
        r = False

        if self.phase == 9:
            w = chr(0) + dixpcommon.txt2raw(frm)
            s = chr(self.chanr) + 3*chr(0) + 'K' + 23*chr(0)
            s += chr(len(w) % 256) + chr(len(w) / 256) + 6*chr(0) + w

            try:
                self.sockt.send(s)
            except socket.error:    
                self.phase = 10
                r = True
            
        return r
         
    def engine(self):     
        # Check received frames if connecion active
        #print "AGWPE phase: %d" % (self.phase)
        if self.phase == 9:
            rq = []
            
            try:
                s = self.sockt.recv(10000)

                # Check for error
                if len(s) == 0:
                    self.phase = 10
                    

                # Process received data
                else:
                    p = s
                    
                    while True:
                        plen = ord(p[28]) + 256 *ord(p[29]) + 36
                        w = p[:plen]

                        if len(w) == plen:
                            rq.append((s[0], w))
                            
                        p = p[plen:]

                        if len(p) == 0:
                            break

            except socket.timeout:
                pass

            except socket.error:
                self.phase = 10
                
            for p in rq:
                if p[1][4] == 'K':
                    xtx = dixpcommon.raw2txt(p[1][37:])
                    
                    if xtx <> '':
                        xsx = (ord(p[0]), xtx)
                        self.rxque.put(xsx)

            return


        # Start connection
        if self.phase == 0:
            self.sockt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sockt.settimeout(0.5)

            try:
                self.sockt.connect((self.servr, self.prtnr))
                self.phase = 1

            except socket.error, s:
                self.phase = 10
                        
            return    

        # Initialize raw frame reception
        if self.phase == 1:
            try:
                self.sockt.send(4*chr(0) + 'k' + 31*chr(0))
                self.sockt.settimeout(0.5)
                self.phase = 9

            except socket.error, s:
                self.phase = 10               
                
            return


        # Initiate disconnection
        if self.phase == 10:
            
            self.srvid = None
            
            try:
                self.sockt.close()

            except socket.error, s:
                pass
            
            self.sockt = None
            self.tmdis = time.time() + 1 * 60 # 1 minute delay after disconnect
            self.phase = 11
            return

        # Delay after disconnection
        if self.phase == 11:
            
            if time.time() > self.tmdis :
                self.phase = 12

            time.sleep(0.1)

            return

        # Reconnect if enabled
        if self.phase == 12:
            if self.recon == True:
                self.phase = 0
            else:
                self.phase = -1

            return
    
            
        # No valid phase found
        return



###############################################################################	
###############################################################################	

def procmain(dev, (udptx, udpgw,udprx, udpcc), (servr, prtnr, chan, ctrl), ptt, debug, mycall):
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
        
    # Setup server connection

    agwpe = AGWPECON()

    agwpe.servr = servr 
    agwpe.prtnr = prtnr


    # Start AGWPE connection

    agwpe.phase = 0

    # Main program loop

    try:
        while True:
            agwpe.engine()

            flag = 0
            
            while True:
                r = agwpe.receive()
                                
                if r == None:
                    break

                try:

                    flag = 1

                    # Process packets received

                    if r[0] == agwpe.chanr:
                        st = "R" + dev + "%d" % (agwpe.chanr) + r[1] # Single channel device

                        if socgw <> None:
                            socgw.send(st)

                        if soctx <> None:
                            soctx.send(st)

                        if soccc <> []:
                            stcc = "DIXPRS2201|" + mycall + "|" + st[:2] + "|" + st[3:]
                            
                            for i in range(0, len(soccc)):
                                try:
                                    soccc[i].sendto(stcc, (udpcc[i][0], udpcc[i][1]))
                                except (socket.error, socket.gaierror):
                                    pass
                        
                except ValueError:
                    continue

            # No Rf frame received, deal with low priority tasks
            if flag == 0:

                r = socrx.receive()

                if r <> None:
                    if r[0] == 'D':

                        if ptt:
                            agwpe.send(r[1:])
                        
                            if soccc <> []:
                                stcc = "DIXPRS2201|" + mycall + "|T" + dev + "|" + r[1:] 
        
                                for i in range(0, len(soccc)):
                                    try:
                                        soccc[i].sendto(stcc, (udpcc[i][0], udpcc[i][1]))
                                    except (socket.error, socket.gaierror):
                                        pass
                        
                    
                else:                    
                    # Send status to main
                    #soctx.send("SA0%d" % (agwpe.phase))
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

    agwpe.stop()


if __name__ == '__main__':

    print "kkk"
