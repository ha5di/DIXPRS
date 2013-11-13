#! /usr/bin/python

####################################################
# APRS digipeater and gateway for amateur radio use
#
# (C) HA5DI - 2012
#
# http://sites.google.com/site/dixprs/
####################################################

import	time
import  binascii
import  sys
import  os

from sqlite3 import *
from dixlibcommon import cvars

import dixlibax25


def finish():
        curdat.close()
        condat.close()

        curopt.close()
        conopt.close()
        
        curtmp.close()
        contmp.close()

        return

    
def IsGatedFrom(stn):
    cmd = "SELECT * FROM gatedlist WHERE tm>%f AND stn='%s'" % (time.time() - 3600.0, stn)

    curtmp.execute(cmd)
    res = curtmp.fetchall()
    
    if len(res) > 0:
        return True
    
    return False       
        

def GetGatedPort(stn):
    cmd = "SELECT * FROM gatedlist WHERE tm>%f AND stn='%s'" % (time.time() - 3600.0, stn)

    curtmp.execute(cmd)
    res = curtmp.fetchone()
    
    if len(res) > 0:
        return res[2]
    
    return -1       
        
#---------------------------    
            
def AddRfHeard(stn, port, hops):
    cmd = "SELECT * FROM heardrf WHERE stn=\'%s\' AND port=%d AND hops=%d" % (stn, port, hops)

    try:
        curtmp.execute(cmd)
    except Error, e:
        print "00000", cmd
    
    res = curtmp.fetchone()

    if res == None:
        cmd = "INSERT INTO heardrf VALUES (\'%s\', %f, %d, %d)" % (stn, time.time(), port, hops)

        try:
            curtmp.execute(cmd)
        except Error, e:
            print "11111", cmd
    else:
        cmd = "UPDATE heardrf SET tm=%f WHERE stn=\'%s\' AND port=%d AND hops=%d" % (time.time(), stn, port, hops)
    
        try:
            curtmp.execute(cmd)
            contmp.commit()
        except Error, e:
            print "22222", cmd

    ############################x 
    
    tmh = int(time.time() / 3600.0)
    
    cmd = "SELECT nr FROM aprsh WHERE stn='%s' AND port=%d AND tmh=%d" % (stn, port, tmh)
    curdat.execute(cmd)
    res = curdat.fetchone()

    if res == None:
        cmd = "INSERT INTO aprsh VALUES('%s', %d, %d, 1)" % (stn, tmh, port)
    else:
        cmd = "UPDATE aprsh SET nr=%d WHERE stn='%s' AND port=%d AND tmh=%d" % (res[0] + 1, stn, port, tmh)
    
    curdat.execute(cmd)        
    condat.commit()
    
    return
    

def AddRfHeardList(stn, port, hops, pos, dist, hdr, dti, inf):    
    cmd = "INSERT INTO heardlist VALUES ('%s', %f, %d, %d,%f, %f, %f, '%s', %d, '%s')" % \
        (stn, time.time(), port, hops, pos[0], pos[1], dist, hdr, dti, inf)
    curtmp.execute(cmd)
    contmp.commit()
    
    # Add to DX lists if heard direct
    if hops == 0 and dist >= 0:
        cmd = "SELECT * FROM dxlst24h WHERE port=%d AND stn='%s'" % (port, stn)
        curdat.execute(cmd)        
        res = curdat.fetchone()

        if res == None:        
            cmd = "INSERT INTO dxlst24h VALUES ('%s', %f, %d, %f, %f, %f)" % (stn, time.time(), port, pos[0], pos[1], dist)
            curdat.execute(cmd)
            condat.commit()
        else:
            if dist >= res[5]:
                cmd = "UPDATE dxlst24h SET dist=%f,tm=%f WHERE stn='%s' AND port=%d" % (dist, time.time(), stn, port)
                curdat.execute(cmd)                                         
                condat.commit()

        cmd = "SELECT * FROM dxlsttot WHERE port=%d AND stn='%s'" % (port, stn)
        curdat.execute(cmd)        
        res = curdat.fetchone()

        if res == None:        
            cmd = "INSERT INTO dxlsttot VALUES ('%s', %f, %d, %f, %f, %f)" % (stn, time.time(), port, pos[0], pos[1], dist)
            curdat.execute(cmd)
            condat.commit()
        else:
            if dist >= res[5]:
                cmd = "UPDATE dxlsttot SET dist=%f,tm=%f WHERE stn='%s' AND port=%d" % (dist, time.time(), stn, port)
                curdat.execute(cmd)                                         
                condat.commit()
    return    
    
 
def GetRfHeard(port, maxhops):
    if port < 0:
        cmd = "SELECT stn, tm, min(hops) FROM heardrf WHERE tm>%f AND hops<=%d GROUP BY stn ORDER BY stn" % (time.time() - 3600.0, maxhops)
    else:        
        cmd = "SELECT stn, tm, min(hops) FROM heardrf WHERE tm>%f AND port=%d AND hops<=%d GROUP BY stn ORDER BY stn" % (time.time() - 3600.0, port, maxhops)
       
    curtmp.execute(cmd)
    res = curtmp.fetchall()
    
    return res    
    
def GetRfCntAll(port):
    res = GetRfHeard(port, 999)
    return len(res)
    
def GetRfCntLoc(port):
    res = GetRfHeard(port, cvars.get('genCFGlocalhops'))
    return len(res)
        
def GetRfCntDir(port):
    res = GetRfHeard(port, 0)
    return len(res)


def IsLocal(stn, maxhops):
    cmd = "SELECT stn, tm, min(hops) FROM heardrf WHERE tm>%f AND hops<=%d AND stn='%s' GROUP BY stn ORDER BY stn" % (time.time() - 3600.0, maxhops, stn)

    curtmp.execute(cmd)
    res = curtmp.fetchall()
    
    if len(res) > 0:
        return True
    
    return False       
    

# Return port number if heard or -1 if not heard
    
def GetRfPort(stn):
    cmd = "SELECT port FROM heardrf WHERE stn='%s' ORDER BY tm DESC" % (stn)
       
    curtmp.execute(cmd)
    res = curtmp.fetchone()
    
    if res <> None:
        return res[0]
    
    return -1         
    
        
#--------------------------------------------    
def putdbpos(stn, (lat, lng), dist):
    cmd = "DELETE FROM posits WHERE stn='%s'" % (stn)
    curdat.execute(cmd)
    
    cmd = "INSERT INTO posits VALUES('%s', %f, %f, %f, %f)" % (stn, time.time(), lat, lng, dist)
    curdat.execute(cmd)    
    condat.commit()
    
    return
    

def getdbposfull(stn):
    cmd = "SELECT * FROM posits WHERE stn=\'%s\' ORDER BY tm DESC LIMIT 1" % (stn)

    try:
        curdat.execute(cmd)
    except Error:
        return ()
    
    res = curdat.fetchone()

    if res == None:
        return ()

    return(res)	
    

def getdbpos(stn):
    res = getdbposfull(stn)    
    
    if res == ():
        return ()
     
    return(res[2], res[3])        

           
######################################################################
# Functions to work with heard list
######################################################################

# Add recieved frame to database

def airheardaddrecord(stn, to, via, port, dir, dist, lng, lat, dti, data):        
    if dir:
        dr = 1
    else:
        dr = 0
    
    tm = time.time()
    

    # Store DX only if valid
    if dr <> 0 and lng <> 0 and lat <> 0 and dist >= 0.0:
        try:    
            cmd = "INSERT INTO dxall VALUES ('%s', '%s', '%s', %f, %d, %d, %f, %f, %f, %d, '%s')" % \
            (stn, to, via, tm, port, dr, dist, lng, lat, ord(dti), binascii.b2a_base64(data))
            curdat.execute(cmd)
            condat.commit()
        except:
            return 1
       
    return 0



# Add sent frame 

def addsentlist(port, dest):        
    cmd = "INSERT INTO sentlist VALUES ('%s', %f, %d)" % (time.time(), port, dest)
    curtmp.execute(cmd)
    contmp.commit()
          
    return 0


# Add gated message to database

def airgatedaddrecord(port, msg):    
    try:    
        cmd = "INSERT INTO gatedlist VALUES ('%s', %f, %d, '%s')" % (msg.split('>')[0], time.time(), port, msg.split(':')[2].strip())
        curtmp.execute(cmd)
        contmp.commit()
    except:
        return 1
        
    return 0


# Add stn heard on Internet to database

def airaddstnnetlist(stn):        
    try:    
        cmd = "DELETE FROM netlist WHERE stn='%s'" % (stn)
        curtmp.execute(cmd)
        cmd = "INSERT INTO netlist VALUES ('%s', %f)" % (stn, time.time())
        curtmp.execute(cmd)
        contmp.commit()
    except:
        return 1
        
    return 0

# Get gated message count for last hour

def getgatedmsgcount(port):        
    if port < 0:
        cmd = "SELECT * FROM gatedlist WHERE tm>%f" % (time.time() - 3600.0)
    else:
        cmd = "SELECT * FROM gatedlist WHERE tm>%f AND port=%d" % (time.time() - 3600.0, port)
        
    try:    
        curtmp.execute(cmd)
    except:
        return 0

    res = curtmp.fetchall()        
    return len(res)


# Get list of directly heard stations in last 1 hour

def airgetdirect1h(port):
    
    res = GetRfHeard(port, 0)
    
    lst = []    
    
    for p in res:
        lst.append(p[0])
        
    return lst


# Return list for ?APRSH query

def GetAprshList(stn, port):
    lst = []
    tmhnow = int(time.time() / 3600.0)
    
    for i in range(0, 8):
        nr = 0
        
        if port < 0:
            cmd = "SELECT nr FROM aprsh WHERE stn='%s' AND tmh=%d" % (stn, tmhnow - i)  
        else:                
            cmd = "SELECT nr FROM aprsh WHERE stn='%s' AND tmh=%d AND port=%d" % (stn, tmhnow - i, port)
            
        curdat.execute(cmd)  
        res = curdat.fetchall()

        for p in res:
            nr += p[0]
        
        lst.append(nr)
        
    return lst            


def GetStnBest(stn):
    cmd = "SELECT * FROM heardlist WHERE stn='%s' AND tm>%f ORDER BY hops,tm DESC LIMIT 1" % (stn, time.time() - 3600.0)    
    curtmp.execute(cmd)    
    res = curtmp.fetchone()     
    return res    

def GetStnLast(stn):
    cmd = "SELECT * FROM heardlist WHERE stn='%s' AND tm>%f ORDER BY tm DESC LIMIT 1" % (stn, time.time() - 3600.0)    
    curtmp.execute(cmd)    
    res = curtmp.fetchone()     
    return res     
    
#########################################################

def GetDxList1h(n, port):
    if port < 0:
        cmd = "SELECT stn,tm,port,dist FROM heardlist WHERE tm>%f AND hops=0 AND dist>=0 ORDER BY dist DESC LIMIT %d" % (time.time() - 3600.0, n)
    else:
        cmd = "SELECT stn,tm,port,dist FROM heardlist WHERE tm>%f AND hops=0 AND dist>=0 AND port=%d ORDER BY dist DESC LIMIT %d" % (time.time() - 3600.0, port, n)

    curtmp.execute(cmd)   
    res = curtmp.fetchall()     
    
    return res

def GetDxList24h(n, port):
    if port < 0:
        cmd = "SELECT stn,tm,port,dist FROM dxlst24h WHERE tm>%f ORDER BY dist DESC LIMIT %d" % (time.time() - 24 * 3600.0, n)
    else:
        cmd = "SELECT stn,tm,port,dist FROM dxlst24h WHERE tm>%f AND port=%d ORDER BY dist DESC LIMIT %d" % (time.time() - 24 * 3600.0, port, n)

    curdat.execute(cmd)   
    res = curdat.fetchall()     
    
    return res


def GetDxListTot(n, port):
    if port < 0:
        cmd = "SELECT stn,tm,port,dist FROM dxlsttot ORDER BY dist DESC LIMIT %d" % (n)
    else:
        cmd = "SELECT stn,tm,port,dist FROM dxlsttot WHERE port=%d ORDER BY dist DESC LIMIT %d" % (port, n)

    curdat.execute(cmd)   
    res = curdat.fetchall()     
    
    return res


def IsConnectedToNet(call):
    cmd = "SELECT tm FROM netlist WHERE tm>%f AND stn='%s' LIMIT 1" % (time.time() - 3600, call)
    curtmp.execute(cmd)
    res = curtmp.fetchone()

    if res == None:
        return 0
        
    return res[0]


def GetTlmData(port):
    # Packets heard
    cmd = "SELECT * FROM heardlist WHERE tm>%f AND port=%d" % (time.time() - 900, port)
    curtmp.execute(cmd)
    res = curtmp.fetchall()
    pktall = len(res) 

    # Packets heard direct
    cmd = "SELECT * FROM heardlist WHERE tm>%f AND hops=0 AND port=%d" % (time.time() - 900, port)
    curtmp.execute(cmd)
    res = curtmp.fetchall()
    pktdir = len(res)

    # Stations heard
    cmd = "SELECT * FROM heardlist WHERE tm>%f AND port=%d GROUP BY stn" % (time.time() - 900, port)
    curtmp.execute(cmd)
    res = curtmp.fetchall()
    stnall = len(res)

    # Stations heard direct
    cmd = "SELECT * FROM heardlist WHERE tm>%f AND hops=0 AND port=%d GROUP BY stn" % (time.time() - 900, port)
    curtmp.execute(cmd)
    res = curtmp.fetchall()
    stndir = len(res) 

    # Packets sent
    cmd = "SELECT * FROM sentlist WHERE tm>%f AND port=%d" % (time.time() - 900, port)
    curtmp.execute(cmd)
    res = curtmp.fetchall()
    pktsnt = len(res)

    return (pktall, pktdir, stnall, stndir, pktsnt)


######################################################################
# Functions for database maintenance
######################################################################

def DbVacuum():
    curdat.execute('VACUUM')
    condat.commit()

    
    curopt.execute('VACUUM')
    conopt.commit()
    
    curtmp.execute('VACUUM')
    contmp.commit()

    return

def DbDatPurge():
    lstlen = 50
    
    curdat.execute('DELETE FROM posits WHERE tm<%f' % (time.time() - 30 * 24 * 3600.0)) # 30 days
    curdat.execute('DELETE FROM aprsh WHERE tmh<%d' % (int(time.time() / 3600.0) - 7)) # 8 hours   
    curdat.execute('DELETE FROM dxlst24h WHERE tm<%f' % (time.time() - 24 * 3600.0)) # 14 hours   
    condat.commit()

    cmd = "SELECT port FROM dxlst24h GROUP BY port"
    curdat.execute(cmd)
    res = curdat.fetchall()
    
    for p in res:
        port = p[0]
    
        cmd = "SELECT dist FROM dxlst24h WHERE port=%d ORDER BY dist DESC LIMIT %d" % (port, lstlen) 
        curdat.execute(cmd)
        res = curdat.fetchall()
    
        if len(res) == lstlen:
            cmd = "DELETE FROM dxlst24h WHERE dist<%f AND port=%d" % (res[lstlen - 1][0], port)
            curdat.execute(cmd)
            condat.commit()     

        cmd = "SELECT dist FROM dxlsttot WHERE port=%d ORDER BY dist DESC LIMIT %d" % (port, lstlen) 
        curdat.execute(cmd)
        res = curdat.fetchall()
    
        if len(res) == lstlen:
            cmd = "DELETE FROM dxlsttot WHERE dist<%f AND port=%d" % (res[lstlen - 1][0], port)
            curdat.execute(cmd)
            condat.commit()     
            
    return
    
def DbTmpPurge():
    curtmp.execute('DELETE FROM heardrf WHERE tm<%f' % (time.time() - 3600.0)) # 1 hour   
    curtmp.execute('DELETE FROM netlist WHERE tm<%f' % (time.time() - 3600.0)) # 1 hour
    curtmp.execute('DELETE FROM gatedlist WHERE tm<%f' % (time.time() - 3600.0)) # 1 hour
    curtmp.execute('DELETE FROM heardlist WHERE tm<%f' % (time.time() - 3600.0)) # 1 hour
    curtmp.execute('DELETE FROM sentlist WHERE tm<%f' % (time.time() - 3600.0)) # 1 hour
    contmp.commit()   
    return

######################################################################
# Functions for outgoing message handling
######################################################################

def msgadd(msgout):
    # Check pending message
    curtmp.execute("SELECT * FROM msgout WHERE stn='%s'" % (msgout[0]))
    res = curtmp.fetchone()

    if res == None:
        curtmp.execute("INSERT INTO msgout VALUES (\'%s\', \'%s\', \'%s\', %d, %d, %f)" % \
        (msgout[0], msgout[1], binascii.b2a_base64(msgout[2]), 1, 0, 0))
        contmp.commit()

    else:
        curtmp.execute("INSERT INTO msgout VALUES (\'%s\', \'%s\', \'%s\', %d, %d, %f)" % \
        (msgout[0], msgout[1], binascii.b2a_base64(msgout[2]), 0, 0, 0))
        contmp.commit()
        
    return


def msgack(ackk):
    # Delete acknowledged message
    curtmp.execute("SELECT * FROM msgout WHERE ack='%s'" % (ackk[2]))
    res = curtmp.fetchall()
    curtmp.execute("DELETE FROM msgout WHERE ack='%s'" % (ackk[2]))
    contmp.commit()

    msgactivate(ackk[0])

    return
        

def msgactivate(stn):
    curtmp.execute("SELECT * FROM msgout WHERE stn=\'%s\' AND status=1" % (stn))
    res = curtmp.fetchone()

    if res <> None:
        return

    # Make next message active
    curtmp.execute("SELECT * FROM msgout WHERE stn=\'%s\' AND status=0 ORDER BY ack" % (stn))
    res = curtmp.fetchone()

    if res == None:
        return

    curtmp.execute("UPDATE msgout SET status=1 WHERE stn=\'%s\' AND ack=\'%s\'" % (stn, res[1]))
    contmp.commit()

    return
    

def msgactivateall():
    curtmp.execute("SELECT stn FROM msgout GROUP BY stn")
    res = curtmp.fetchall()

    for p in res:
        msgactivate(p[0])


def msggetnext():
    try:
        curtmp.execute("SELECT * FROM msgout WHERE status=1 AND txtime<%f ORDER BY ack" % (time.time()))
        res = curtmp.fetchone()

        if res == None:
            return []

        if res[4] >= 10:
            curtmp.execute("DELETE FROM msgout WHERE stn='%s' AND ack='%s'" % (res[0], res[1]))
            msgactivate(res[0])
            contmp.commit()
            return []

        curtmp.execute("UPDATE msgout SET nr=%d, txtime=%f WHERE stn='%s\' AND ack='%s'" % \
        (res[4] + 1, time.time() + 10.0, res[0], res[1]))
        contmp.commit()

    except:
        return []
    
    return [res[0], res[1], binascii.a2b_base64(res[2])]

def msggetacknr():
    curopt.execute("SELECT val FROM options WHERE par='ackcnt'")
    res = curopt.fetchone()

    if res == None:
        return 0

    nr = int(res[0])

    nrnew = nr + 1

    if nrnew > 99999:
        nrnew = 0

    curopt.execute("UPDATE options SET val='%d' WHERE par='ackcnt'" % (nrnew))
    conopt.commit()
    return nr


    
######################################################################
def start(): 
    global condat
    global conopt
    global contmp
    
    global curdat
    global curopt
    global curtmp

    condat = connect(os.path.dirname(sys.argv[0]) + '/dixprsdta.db')
    conopt = connect(os.path.dirname(sys.argv[0]) + '/dixprsopt.db')
    contmp = connect(os.path.dirname(sys.argv[0]) + '/dixprstmp.db')
    
    curdat = condat.cursor()
    curopt = conopt.cursor()
    curtmp = contmp.cursor()

    
    #################################

    try:
        curdat.execute('SELECT * FROM posits')
    except:
        curdat.execute('''CREATE TABLE posits (stn text, tm real, lng real, lat real, dist real)''')
        condat.commit() 

    try:
        curdat.execute('SELECT * FROM aprsh')
    except:
        curdat.execute('''CREATE TABLE aprsh (stn text, tmh integer, port integer, nr integer)''')
        condat.commit()        

    try:
        curdat.execute('SELECT * FROM dxlst24h')
    except:
        curdat.execute('''CREATE TABLE dxlst24h (stn text, tm real, port integer, lng real, lat real, dist real)''')
        condat.commit()        

    try:
        curdat.execute('SELECT * FROM dxlsttot')
    except:
        curdat.execute('''CREATE TABLE dxlsttot (stn text, tm real, port integer, lng real, lat real, dist real)''')
        condat.commit()        
 
    # TMP
       
    try:
        curtmp.execute('SELECT * FROM heardrf')
    except:
        curtmp.execute('''CREATE TABLE heardrf (stn text, tm real, port integer, hops integer)''')
        contmp.commit() 
         
    try:
        curtmp.execute('SELECT * FROM netlist')
    except:
        curtmp.execute('''CREATE TABLE netlist (stn text, tm real)''')
        contmp.commit()        

    try:
        curtmp.execute('SELECT * FROM heardlist')
    except:
        curtmp.execute('''CREATE TABLE heardlist (stn text, tm real, port integer, hops integer, \
            lng real, lat real, dist real, hdr text, dti integer, inf text)''')
        contmp.commit()        

    try:
        curtmp.execute('SELECT * FROM netlist')
    except:
        curtmp.execute('''CREATE TABLE netlist (stn text, tm real)''')
        contmp.commit()        

    try:
        curtmp.execute('SELECT * FROM gatedlist')
    except:
        curtmp.execute('''CREATE TABLE gatedlist (stn text, tm real, port integer, dst text)''')
        contmp.commit()        

    try:
        curtmp.execute('SELECT * FROM sentlist')
    except:
        curtmp.execute('''CREATE TABLE sentlist (tm real, port integer, dest integer)''')
        contmp.commit()        
        
    try:
        curtmp.execute('SELECT * FROM msgout')
    except:
        curtmp.execute('''CREATE TABLE msgout (stn text, ack text, msg text, status int, nr int, txtime float)''')
        contmp.commit()        

    #####################
    
    
    try:
        curopt.execute('SELECT * FROM options')
    except:
        curopt.execute('''CREATE TABLE options (par text, val text)''')
        conopt.commit()    
    
    ##################################
        
    curopt.execute("SELECT val FROM options WHERE par='ackcnt'")
    res = curopt.fetchone()
    
    if res == None:
        curopt.execute("INSERT INTO options VALUES ('ackcnt', '0')")
        conopt.commit()
    
condat = None
conopt = None
contmp = None

curdat = None
curopt = None
curtmp = None

        
