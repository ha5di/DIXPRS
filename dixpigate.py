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

import  hdump  
        
###############################################################################
# Calculate iGate pass code for callsign
#
# Input:	call - callsign
#
# Return:	pass code
###############################################################################	

def callpass(call):

    s = call.split('-')
    s[0] += chr(0)
    hash = 0x73e2
    
    for i in range(0, len(s[0])-1, 2):
        hash ^= ord(s[0][i]) << 8
        hash ^= ord(s[0][i+1])
        
    return hash & 0x7fff
    

class IGATECON:
    def __init__(self):
        self.phase = -1
        self.sockt = None
        self.servr = None
        self.prtnr = 14580
        self.filtr = None
        self.ruser = None
        self.versn = ''
        self.srvid = ''
        self.tmdis = None
        self.recon = True
        self.rxque = Queue.Queue()
        self.igque = Queue.Queue()
        self.tmstr = None           # Connection start time
        self.tmlst = 0              # Last line reception time
        self.connr = 0
        self.bcntx = None
        self.partl = ''             # Partial line buffer
        
        return

    def stop(self):
        if self.sockt <> None:
            self.recon = False
            self.phase = -1
            
            try:
                self.sockt.close()
            except socket.error, s:
                pass
            
        return

    def receive(self):
        try:
            r = self.rxque.get(False)
        except Queue.Empty:
            return None

        return r

    def send(self, s):
        if self.phase == 9:         
            try:
                self.sockt.send(s + '\r')
            except socket.error, s:
                self.phase = 10
                print "PHASE ERROR 2"
        return

    # Engine        
    def engine(self):
        #print "STATUS", self.phase
        rs = []
              
        # Check received frames if connecion active
        if self.phase > 0 and self.phase < 10:
            try:
                r = self.sockt.recv(1000)

                # Check for error
                if len(r) == 0:
                    self.phase = 10
                    print "PHASE ERROR 1"
                    return
                
                
                # Reset timeout
                self.tmlst = time.time()
                #print "RESET"
                   
                wl = self.partl + r
                self.partl = ''
                rl = wl.splitlines()
                                    
                # Is there a partial frame?
                if len(wl) == len(wl.strip()):
                    # Partial
                    self.partl = rl[len(rl) - 1]                   
                    
                    if len(rl) > 1:
                        for i in range(0, len(rl) - 1): 
                            self.igque.put(rl[i])               

                else:
                    for i in range(0, len(rl)): 
                        self.igque.put(rl[i])                                                        
                        
                # Process received lines
                
                while True:                   
              
                    try:
                        p = self.igque.get(False)
                    except Queue.Empty:
                        break
                                           
                    # Server message
                    if len(p) > 0:
                        if p[0] == '#':
                            w = p.split()
                            
                            if len(w) >= 6 and self.srvid == '':
                                
                                if w[0] == '#' and w[1] == 'logresp' and w[2] == self.ruser and w[4] == 'server':
                                    
                                    # Pass code accepted                                    
                                    if w[3] == 'verified,':
                                        self.srvid = w[5].split(',')[0]
                                        self.connr += 1
                                    else:        
                                        print "PASS CODE IS REJECTED"
                                        self.phase = 10
                            else:  
                                # Server messages
                                if len(w) >= 2:
                                    if w[1] == 'javAPRSSrvr' or w[1] == 'aprsc':
                                        if len(w) >= 5:                                   
                                            if w[3] == 'port':
                                            
                                                # Reconnect
                                                if w[4] == 'full.' or w[4] == 'unavailable.': 
                                                    print "CAN't CONNECT, low server resources"
                                                    self.phase = 10

                        # APRS frame
                        else:
                            rs.append(p)
                    
            except socket.timeout:
                pass

            except socket.error, e:
                self.phase = 10
                print "PHASE ERROR 3"

        # Normal reception
        if self.phase == 9:
            if rs <> []:
                for p in rs:
                    self.rxque.put(p)
                  
            # Check for 5 minutes rx timeout
            if time.time() - self.tmlst > 5 * 60:
                self.phase = 10
                print "*** Connection lost (timeout)"

            return

        # Start connection
        if self.phase == 0:            
            self.tmstr = time.time()
            self.sockt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sockt.settimeout(10.0)

            try:
                #print "Connecting", self.servr, self.prtnr
                self.sockt.connect((self.servr, self.prtnr))
                self.phase = 1
                print "*** Connection established"

            except socket.error, s:
                self.phase = 10
                print "*** Connection failure"
            return    

        # Send login
        if self.phase == 1:
            try:
                self.sockt.send('user ' + self.ruser + ' pass ' + '%d' % (callpass(self.ruser)) + ' vers ' + self.versn + ' filter ' + self.filtr + '\r')
                self.phase = 2

            except socket.error, s:
                self.phase = 10
                print "PHASE ERROR 7"
            return

        # Wait for remote server id
        if self.phase == 2:
            if self.srvid <> '':
                self.phase = 3
                
            return

        # Send position
        if self.phase == 3:
            #self.sendmy(self.bcntx)
            
            self.sockt.settimeout(0.0001)
            self.phase = 9
            print "*** Connection successful to " + self.srvid

            if self.bcntx <> None:
                self.send(self.bcntx)
            
            return

        # Initiate disconnection
        if self.phase == 10:
            print "*** Starting 1 minute delay before reconnect"
            
            self.srvid = ''
            
            try:
                self.sockt.shutdown(socket.SHUT_RDWR)
                self.sockt.close()
            except socket.error, s:
                pass
            
            self.sockt = None
            self.tmdis = time.time() + 1 * 60 # 1 minute delay after disconnect
            self.phase = 11
            return

        # Delay after disconnection
        if self.phase == 11:
            #print "PHASE 11"
    
            if time.time() > self.tmdis :
                self.phase = 12

            return

        # Reconnect if enabled
        if self.phase == 12:
            print "*** Trying to reconnect"
            if self.recon == True:
                self.phase = 0
            else:
                self.phase = -1

            return  
            
        # No valid phase found
        return

    
###############################################################################
#
# MAIN PROGRAM
#
###############################################################################	

def procmain(udpbase, servr, prtnr, ruser, filtr, versn):
    #################################################
    # Default settings
    #################################################

    #################################################
    # Initialize variables
    
    igate = IGATECON()

    igate.servr = servr
    igate.prtnr = prtnr
    igate.ruser = ruser
    igate.filtr = filtr
    igate.versn = versn
           
    # Setup UDP listening port

    socrx = dixdrvudp.UDPRx(udpbase + 1)
    socrx.settimeout(1.0)

    # Setup UDP sending port

    soctx = dixdrvudp.UDPTx(udpbase)

    # Setup server connection

    igate.phase = 0

    # Main program loop

    while True:
        try:
            # Wait for data or command
            # This is the highest priority event
            
            v = socrx.receive()
            
            t1 = time.time()
    
            # Process packets received from UDP command/data port
    
            if v <> None: 
                if True:
    
                #if v[1][0] == '127.0.0.1':                    
                    cmd = v[0]
                    
                    # Rf->Igate gating data
                    if cmd == 'R':
                        w = v[3:]
    
                        # Unwrap encapsulated frames for gating
                        while True:
                            k = w.find(':')
    
                            if k < 0:
                                break
    
                            try:
                                id = w[k + 1]
                            except IndexError:
                                break
    
                            if id <> '}':
                                break
    
                            w = w[k + 2:]
                      
                        # Is it a generic query?           
                        k = w.find(':')
    
                        if k > 6:
                            try:
                                id = w[k + 1]
                                head = w[:k]
                                tail = w[k + 1:]
    
                                if tail[0] <> '?':
                                   if head.find('TCPIP') < 0 and head.find('TCPXX') < 0 \
                                        and head.find('NOGATE') < 0  and head.find('RFONLY') < 0:
                                    
                                        r2 = head + ',qAR,%s:' % (igate.ruser) + tail
    
                                        # Send r2 to igate
                                        igate.send(r2)
                                              
                            except IndexError:
                                pass
                                        
                    # Data frame received
                    elif cmd == 'D':
                        igate.send(v[1:])
    
                    # Termination command received
                    elif cmd == 'Q':
                        break
                        
            else:
                # Do lower priority job
    
                # Send status / life beat signal to main program
                soctx.send('SI0' + "%d|%s|%d" % (igate.phase, igate.srvid, igate.connr))
                
                # Check Internet incoming data server
                while True:
                    igate.engine()
                    r = igate.receive()
    
                    # Process received lines from server
                    if r <> None:
                        soctx.send('RI0' + r)
                    else:
                        break

        except KeyboardInterrupt:
            pass
                    
    print "igate terminating"    
    # Shutting down
    socrx.close()
    soctx.close()
    igate.stop()
    # ---- End of procmain
