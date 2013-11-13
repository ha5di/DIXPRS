#! /usr/bin/python

####################################################
# APRS digipeater and gateway for amateur radio use
#
# (C) HA5DI - 2012
#
# http://sites.google.com/site/dixprs/
####################################################

import  socket

import  hdump

        
class UDPRx:
    def __init__(self, port):
        self.socrx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socrx.bind(('', port))
        self.socrx.settimeout(0.5)
        return

    def receive(self):
        try:
            data, adr = self.socrx.recvfrom(1000)
        
            # Process packets received

            if len(data) == 0:
                return None
                
            if adr[0] <> '127.0.0.1':
                return None               

            return data

        except socket.timeout:        
            return None

    def settimeout(self, tout):
        self.socrx.settimeout(tout)
        
    def close(self):
        self.socrx.close()
        return


class UDPTx:
    def __init__(self, port):
        self.servr = 'localhost'
        self.portn = port
        self.soctx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.soctx.settimeout(0.5)
        return

    def send(self, data):
        self.soctx.sendto(data, (self.servr, self.portn))
        return

    def settimeout(self, tout):
        self.soctx.settimeout(tout)
        
    def close(self):
        self.soctx.close()
        return

    
