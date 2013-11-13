#! /usr/bin/python

####################################################
# APRS digipeater and gateway for amateur radio use
#
# (C) HA5DI - 2012
#
# http://sites.google.com/site/dixprs/
####################################################

def readcfg(fname):
    
    try:
        fp = open(fname)

    except IOError:
        return []

    lst = [['DEFAULT', {}]]
    n = 0

    while True:
        s = fp.readline()
        
        if len(s) == 0:
            break
        
        s = s.strip()

        if len(s) == 0:
            continue
        
        ch = s[0]

        if ch == ';' or ch == '#' or ch == "'":
            continue


        if s[0] == '[' and s[-1] == ']':
            n += 1
            lst.append([s[1:-1].upper(), {}])

        else:
            k = s.find('=')

            if k < 0:
                continue

            p1 = s[:k].strip()
            p2 = s[k + 1:].strip()

            lst[n][1][p1.upper()] =  p2
            
    fp.close()

    return lst


def getcfgsection(cfg, section):
    s = section.upper()

    ret = []
    
    for p in cfg:
        if p[0] == s:
            ret.append(p[1])

    return ret


def yesno(par):
    s = par.upper()

    if s == '1' or s == 'Y' or s == 'YES' or s == 'TRUE':
        return True

    return False
    

def hostadr(s):
    w = s.split(':')
    
    if len(w) <> 2:
        return ()
        
    host = w[0]
    
    try:
        port = int(w[1])             
    except ValueError:
        return ()
        
    return (host, port)        
    
    