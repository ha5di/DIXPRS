#! /usr/bin/python

####################################################
# APRS digipeater and gateway for amateur radio use
#
# (C) HA5DI - 2012
#
# http://sites.google.com/site/dixprs/
####################################################

###############################################################################
# Convert AX25 frame from text to internal format
#
# Input:	txt - frame in text format
#
# Return:	frame in internal format
###############################################################################	
    		
def txt2vir(txt):

    k = txt.find(':')
    
    if k <= 0:
        return []

    try:        
        inf = txt[k + 1:]   
        hdr = txt[:k]
        
        w = hdr.split('>')

        digilst = []
        
        for p in w[1].split(','):
            if p[-1] == '*':
                digilst.append([p[:-1], 1])
            else:
                digilst.append([p, 0])
                
        if len(digilst) == 1:
            return [w[0], digilst[0][0], [], inf]
        else:                   
            return [w[0], digilst[0][0], digilst[1:], inf]

    except:
        return []
    
###############################################################################
# Convert AX25 frame from internal to text format
#
# Input:	vir - frame in internal format
#
# Return:	frame in text format
###############################################################################	

def vir2txt(vir):

    if len(vir) <> 4:
        return ''
    
    txt = vir[0] + '>' + vir[1]
    
    for p in vir[2]:
        txt += ',' + p[0]
	
        if p[1] <> 0:
            txt += '*'

    txt += ':' + vir[3]
    
    return txt

###############################################################################	
###############################################################################	

def IsInvalidCall(s):
    w = s.split('-')

    if len(w) > 2:
        return True

    if len(w[0]) < 1 or len(w[0]) > 6:
        return True

    for p in w[0]:
        if not (p.isalpha() or p.isdigit()):
            return True        
        
    if w[0].isalpha() or w[0].isdigit():
        return True 
        
    if len(w) == 2:
        try:        
            ssid = int(w[1]) 
                
            if ssid < 0 or ssid > 15:
                return True
                        
        except ValueError:
            return True
            
    return False        

###############################################################################

def IsDirect(frm):
    for p in frm[2]:
        if p[1] <> 0:
            return False
            
    return True	
    
def GetHops(frm):
    n = 0
    
    for p in frm[2]:
        if p[1] == 0:
            break
            
        n += 1

    return n                    
    
    
            
