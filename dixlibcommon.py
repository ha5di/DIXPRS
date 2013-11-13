#! /usr/bin/python

####################################################
# APRS digipeater and gateway for amateur radio use
#
# (C) HA5DI - 2012
#
# http://sites.google.com/site/dixprs/
####################################################

import  Queue


def isnetconnected(ax):
    for i in range(0, len(ax[2])):
        if ax[2][i][0] == 'TCPIP' and ax[2][i][1] <> 0:
            if ax[2][i + 1][0] == 'qAC':
                return True

    return False
    

class GLOBALVARS:
    def __init__(self):
        self.v = {}
        
    def put(self, key, val):
        self.v[key] = val
        return

    def get(self, key):
        try:
            ret = self.v[key]
        except NameError:
            ret = None

        return ret


cvars = GLOBALVARS()

msgqueue = Queue.Queue()
ackqueue = Queue.Queue()


igtport = None
