#! /usr/bin/python

####################################################
# APRS digipeater and gateway for amateur radio use
#
# (C) HA5DI - 2012
#
# http://sites.google.com/site/dixprs/
####################################################

import  Queue
import  time
import  platform
import  dixlibsql
import  dixlibax25
import  dixlibgeo
import  dixprscommon
import  dixlibaprs

from dixlibcommon import *
from dixpcommon import radioports

dupls = {}
          
def SendMy2Autoport(stn, s):
    igw = cvars.get('igtport')

    # Was receiving station heard on Rf?
    reprt = dixlibsql.GetRfPort(stn)
    repfl = 0

    if reprt >= 0:

        # Is receiving station connected to NET?
        if dixlibsql.IsConnectedToNet(stn) == 0:
            repfl = 1

    if repfl <> 0:
        #radioports[reprt].sendmynochk(s)
        radioports[reprt].sendmy(s)
    else:
        if igw <> None:
            igw.sendmy(s)
        else:
            for p in radioports:
                print
                p.sendmy(s)            

    return
        
        
def GetDestcall(s):
    w = s.split(':')

    destcall = ''
    
    if len(w) >= 3:
        destcall = w[1].strip()

    return destcall


def msgproc(ax): 
    global dupls
    msgout = []

    if len(ax) < 2:
        return 1

    if len(ax[1]) <> 4:
        return 2

    if len(ax[1][3]) <  12:
        return 3
                
    msgport = ax[0]
    msgfrom = ax[1][0]
    msgdest = ax[1][3][1:10].strip()
    msgbody = ax[1][3][11:].strip()
    msgdupl = False
    msgidnr = ''


    # Check NWS/BOM bulletins gating from IS to Rf
    if msgport < 0:
        if msgdest.find('NWS') == 0:           
            for rxp in range(0, len(radioports)): 
                if radioports[rxp].gtnws:          
                    axg = [ax[1][0], ax[1][1], [['TCPIP', 0], [cvars.get('genCFGcall'), 1]], ax[1][3]]                        
                    gts = dixlibax25.vir2txt(axg)
                    radioports[rxp].sendgate('}' + gts)
                    dixlibsql.airgatedaddrecord(rxp, gts)             
                
            return 4                                                

        if msgdest.find('BOM') == 0:           
            for rxp in range(0, len(radioports)): 
                if radioports[rxp].gtbom:          
                    axg = [ax[1][0], ax[1][1], [['TCPIP', 0], [cvars.get('genCFGcall'), 1]], ax[1][3]]                        
                    gts = dixlibax25.vir2txt(axg)
                    radioports[rxp].sendgate('}' + gts)
                    dixlibsql.airgatedaddrecord(rxp, gts)             

            return 4                                                

    igw = cvars.get('igtport')
    
    k = msgbody.find('{')

    if k >= 0:
        msgidnr = msgbody[k+1:]
        msgbody = msgbody[:k]

    #print ">>>> MSG DATA:", msgport, msgdest, msgbody, msgidnr                    

    # Is message addressed to us?
    if msgdest == cvars.get('genCFGcall'):

        ################################################
        # Message for us
        ################################################
        
        # Send ACK if requested
        if msgidnr <> '':
            s = ":%-9s:ack%s" % (msgfrom, msgidnr)
            #print "--- SEND ACK:", s

            SendMy2Autoport(msgfrom, s)

            # Check duplication                            
            try:
                if dupls[msgfrom + ' ' + msgidnr]:
                    msgdupl = True

            except:
                pass

            # Add msg ID to cache
            dupls[msgfrom + ' ' + msgidnr] = time.time()
       
        # Check message type  
        if msgbody[0:3] == 'ack':
            #print "ACK RECEIVED", msgfrom, msgbody
            ackqueue.put([msgfrom, msgbody[:3], msgbody[3:]])
            
        if msgbody[0:3] == 'rej':
            #print "REJ RECEIVED"
            ackqueue.put([msgfrom, msgbody[:3], msgbody[3:]])
        
        elif (msgbody[0] == '?' or msgbody[0] == '!') and not msgdupl:

        ################################################
        # Process queries and commands
        ################################################
              
            #print ">>>> DIRECTED QUERY FOR US"
                                    
            
            qcmd = msgbody.upper().split()
            

            #######################
            # Process commands
            #######################

            if msgbody[0] == '!':
                answ = 'Command ' + msgbody + ' is unknown'
                cmd = ''
                
                if qcmd[0] == '!APRS':
                    cmd = '?APRS?'

                elif qcmd[0] == '!IGATE':
                    cmd = '?IGATE?'
                    
                elif qcmd[0] == '!WX':
                    cmd = '?WX?'

                if cmd <> '':
                    answ = "Query %s sent to radio port(s)" % (cmd)

                    for p in radioports:
                        p.sendmy(cmd)


            else:

                #######################
                # Process queries
                #######################
                
                answ = 'Query ' + msgbody + ' is not implemented yet'
                nrc, cmd = CmdNorm(qcmd[0][1:])

                cmd = '?' + cmd

                if nrc == 0:
                    answ = "Query %s unknown" % (qcmd[0])
                    
                elif nrc > 1:
                    answ = answ = "Query %s too short" % (qcmd[0])

                else:                                

                    ################################
                    # Standard directed queries
                    ################################
                    
                    if cmd == '?APRSD':        
                        hrd = None
                        
                        if len(qcmd) == 1:
                            prtnr = -1               
                            hrd = dixlibsql.airgetdirect1h(prtnr)    
                        else:
                            try:
                                prtnr = int(qcmd[1])                            

                                if prtnr < 0 or prtnr >= len(radioports):
                                    answ = "Port %s doesn't exist"  % (qcmd[1])
    
                                else:                                                                                             
                                    hrd = dixlibsql.airgetdirect1h(prtnr)

                            except:
                                answ = "Wrong port format: %s" % (qcmd[1])

                        if hrd <> None:                                                    
                            if len(hrd) == 0:
                                answ = 'Directs=None'
    
                            else:
                                if prtnr < 0:
                                    v = ''
                                else:                                    
                                    v = 'AIR%d: ' % (prtnr)
                                
                                for i in range (0, len(hrd)):
                                    if i % 5 == 0 and i <> 0:
                                        if prtnr < 0:
                                            v += '\r'
                                        else:
                                            v += '\rAIR%d: ' % (prtnr) 
    
                                    v += hrd[i] + ' '
    
                                answ = v                                    

                            
                    elif cmd == '?APRSH':
                        if len(qcmd) == 1:
                            answ = 'No callsign provided'

                        else:                                
                            wlst = dixlibsql.GetAprshList(qcmd[1], -9)
                            answ = "%s " % (qcmd[1])

                            if len(wlst) == 0:
                                answ += "was not heard in last 8 hours"
                            else:
                                answ += "heard:"

                                for plst in wlst:
                                    if plst == 0:
                                        answ += ' .'
                                    else:
                                        answ += " %d" % (plst)
                            
                    elif cmd == '?APRSM':
                        answ = 'No undelivered message(s) for you'
                    
                    elif cmd == '?APRSO':
                        answ = 'No object(s) provided by this node'

                    elif cmd == '?APRSP':
                        
                        
                        if msgport < 0:
                            igw.sendmy(igw.bcntx)
                                
                        else:
                            radioports[msgport].sendmy(radioports[msgport].bcntx)
                            
                        answ = "Position report sent"
                    
                    elif cmd == '?APRSS':
                        s = '>' + cvars.get('genCFGstat')

                        if msgport < 0:
                            igw.sendmy(s)
                        
                        else:
                            radioports[msgport].sendmy(s)
                            
                        answ = "Status report sent"                                                       

                    elif cmd == '?APRST' or cmd == '?PING?':
                        s = dixlibax25.vir2txt(ax[1])
                        s = s.split(':')[0]
                        answ = 'Path - ' + s

                    #############################
                    # Non-standard queries
                    #############################

                    elif cmd == '?DATE' or cmd == '?TIME':
                        answ = time.strftime("Date: %d-%m-%Y %H:%Mz", time.gmtime())
                    
                    elif cmd == '?DX':
                        
                        if cvars.get('genCFGmetric'):
                            unit = 'km'
                        else:
                            unit = 'mi'

                        if len(qcmd) == 1:               
                            prtnr = -1    
                        else:
                            try:
                                prtnr = int(qcmd[1])                            

                                if prtnr < 0 or prtnr >= len(radioports):
                                    answ = "Port %s doesn't exist"  % (qcmd[1])
                                    prtnr = None

                            except:
                                answ = "Wrong port format: %s" % (qcmd[1])
                                prtnr = None

                        if prtnr <> None:                                                        
                            w = dixlibsql.GetDxList1h(1, prtnr)
    
                            if len(w) == 0:
                                answ = " 1h: None\r"
                            else:
                                ww = time.strftime("%d-%m-%Y %H:%Mz", time.gmtime(w[0][1]))
                                answ = " 1h: %+9s %s on %12s AIR%d\r" % (w[0][0], dixlibgeo.fmtdist(w[0][3], cvars.get('genCFGmetric')), ww, w[0][2])
                                
                            w = dixlibsql.GetDxList24h(1, prtnr)
    
                            if len(w) == 0:
                                answ += "24h: None\r"
                            else:
                                ww = time.strftime("%d-%m-%Y %H:%Mz", time.gmtime(w[0][1]))
                                answ += "24h: %+9s %s on %12s AIR%d\r" % (w[0][0], dixlibgeo.fmtdist(w[0][3], cvars.get('genCFGmetric')), ww, w[0][2])
      
                            w = dixlibsql.GetDxListTot(1, prtnr)
    
                            if len(w) == 0:
                                answ += "All: None\r"
                            else:
                                ww = time.strftime("%d-%m-%Y %H:%Mz", time.gmtime(w[0][1]))
                                answ += "All: %+9s %s on %12s AIR%d\r" % (w[0][0], dixlibgeo.fmtdist(w[0][3], cvars.get('genCFGmetric')), ww, w[0][2])
                          
                    elif cmd == '?HELP':
                        answ =  '?APRSD ?APRSH ?APRSM ?APRSO ?APRSP\r'
                        answ += '?APRSS ?APRST ?PING?\r'
                        answ += '?DATE ?DX ?HELP ?INFO ?OWNER ?PORTS ?TIME\r'
                        answ += '?TYPE ?UPTIME ?VERSION ?IGATE?'


                    elif cmd == '?INFO':
                        if len(qcmd) == 1:
                            answ = 'No callsign provided'

                        else:
                            answ = ''                         
                            
                            res1 = dixlibsql.getdbposfull(qcmd[1])

                            if len(res1) <> 0:
                                if time.time() - res1[1] >= 3660.0:
                                    ww = time.strftime("%d-%m-%Y %H:%Mz", time.gmtime(float(res1[1]))                                        )
                                    answ += "Posit %0.4f/%0.4f %s on %s\r" % (res1[2], res1[3], dixlibgeo.fmtdist(res1[4], cvars.get('genCFGmetric')), ww)
                                else:
                                    answ += "Posit %0.4f/%0.4f %s %d mins ago\r" % (res1[2], res1[3], dixlibgeo.fmtdist(res1[4], cvars.get('genCFGmetric')), (time.time() - res1[1]) / 60.0)
                                                                                                           
                            res3 = dixlibsql.GetStnBest(qcmd[1])       
 
                            if res3 <> None:
                                if res3[3] == 0:
                                    answ += "Heard direct on AIR%d %d mins ago\r" % (res3[2], (time.time() - res3[1]) / 60.0)
                            
                                else:
                                    viatxt = res3[7]
                                    idxtxt = viatxt.find(',')
                                    
                                    if idxtxt > 0:
                                        viatxt = viatxt[idxtxt + 1:]
                                        answ += "Heard best via %s on AIR%d %d mins ago\r" % (viatxt, res3[2], (time.time() - res3[1]) / 60.0)

                                    res3 = dixlibsql.GetStnLast(qcmd[1])
                                    viatxt = res3[7]
                                    idxtxt = viatxt.find(',')
                                    
                                    if idxtxt > 0:
                                        viatxt = viatxt[idxtxt + 1:]
                                        answ += "Heard last via %s on AIR%d %d mins ago\r" % (viatxt, res3[2], (time.time() - res3[1]) / 60.0)

                            else:
                                res4 = dixlibsql.GetAprshList(qcmd[1], -1)
                                
                                for infidx in range(0, 8):
                                    if res4[infidx] > 0:
                                        answ = "Heard on Rf %d hours ago\r" % (infidx)                                        
                                        break
                                                                                                                                                                                              
                            res2 = dixlibsql.IsConnectedToNet(qcmd[1])
                            
                            if res2 <> 0:
                                answ += "Heard on Net %d mins ago\r" % ((time.time() - res2) / 60.0)
                                
                            if answ == '':
                                answ = "No info stored on %s" % (qcmd[1])                                

                    elif cmd == '?OWNER':
                        answ = 'Owner: ' + cvars.get('genCFGowner')

                    elif cmd == '?PORTS':

                        if igw == None:
                            answ = "iGate closed\r"
                        else:
                            answ = "IS % s:%d (%s) %d/%d\r" % (igw.srvid, igw.srvpr, igw.srvfl, igw.connr, cvars.get('igwSTATrescnt'))

                        if cvars.get('webCFGport') <> None:
                            answ += 'WEB %d\r' % (cvars.get('webCFGport'))
                            
                        for i in range(0, len(radioports)):
                            answ += "AIR%d (%s) %s\r" % (i, radioports[i].hwtyp, radioports[i].pdesc)
                            
                    elif cmd == '?TYPE':
                        answ = "It's DIXPRS by Bela, HA5DI"
                            

                    elif cmd == '?UPTIME':
                        uptd = (time.mktime(time.gmtime()) - time.mktime(cvars.get('sysVARstart'))) / 86400.0
                        upth = (uptd - int(uptd)) * 24.0
                        uptm = (upth - int(upth)) * 60.0
                        answ = time.strftime("Up since %d %b %Y %H:%Mz ",   cvars.get('sysVARstart'))
                        answ += "(%d days %d hours %d mins)" % (int(uptd), int(upth), int(uptm))


                    elif cmd == '?VERSION':
                        answ = dixprscommon.version +  ' (' + dixprscommon.versdat + ') on ' + platform.uname()[0] + \
                        ' ' + platform.uname()[2] + ' (' + platform.uname()[4] + '), Python ' + platform.python_version()

                    elif cmd == '?IGATE?':
                        
                        if len(qcmd) == 1:
                            prtnr = -1               
                        else:
                            try:
                                prtnr = int(qcmd[1])                            

                                if prtnr < 0 or prtnr >= len(radioports):
                                    answ = "Port %s doesn't exist"  % (qcmd[1])
                                    prtnr = None
    
                            except:
                                answ = "Wrong port format: %s" % (qcmd[1])
                                prtnr = None
                        
                        if prtnr <> None:
                            answ = dixlibaprs.mkcaptxt(prtnr)
                    
                    else:
                        answ = "Query error #1"                            


            # Send reply
            answx = []
            
            for p in answ.splitlines():
                ww = p.rstrip()
                if len(ww) == 0:
                    continue

                answx.append(ww)

            if len(answx) <= 1:
                answ = answx

            else:
                answ = []
                ii = 1

                for p in answx:
                    answ.append("(%d/%d) %s" % (ii, len(answx), p))
                    ii += 1                                
                

            # Add line numbers if needed
            for p in answ:
                s = ":%-9s:%s" % (msgfrom, p)

                if msgidnr <> '':
                    ackstr = "%d" % (dixlibsql.msggetacknr())
                    s += "{" + ackstr
                    msgout = [msgfrom, ackstr, s]
                        
                    msgqueue.put(msgout)
                else:
                    SendMy2Autoport(msgfrom, s)
                    
        elif not msgdupl:
            #print ">>>> MSG FOR US"
            pass         
    elif ax[0] < 0:

        ################################################
        # Message not for us and received from Internet
        ################################################

        gt = 0
        
        # Is receiving station connected to NET?
        if dixlibsql.IsConnectedToNet(msgdest) == 0:

            # Was sending station heard on Rf?
            if dixlibsql.GetRfPort(msgfrom) < 0:
                # Start of APRS4R loop fix
                #fl = 0
                #
                #for p in ax[1][2]:
                #    if p[0] == 'qAC':
                #        fl = 1
                #        break
                # End og APRS4R loop fix

                # Check TCPXX, NOGATE or RFONLY in header
                fl = 1
                
                for p in ax[1][2]:
                    
                    if p[0] == 'NOGATE' or p[0] == 'RFONLY' or p[0] == 'TCPXX':
                        fl = 0
                        break
                
                # Can be gated
                if fl <> 0:

                    # Is receiving station local?
                    if dixlibsql.IsLocal(msgdest, cvars.get('genCFGlocalhops')):

                        # Is range based filtering enabled?
                        if cvars.get('genCFGmsgrange') <> None:

                            # Is postion known?
                            ps = dixlibsql.getdbpos(msgdest)
                            
                            if len(ps) <> 2:                                                            
                                gt = 1  # Position not known, gate based on hop count
                            else:
                                dist = dixlibgeo.qradist(ps, (cvars.get('genCFGlati'), cvars.get('genCFGlong')))                            
    
                                # Gate if within range
                                if dist < cvars.get('genCFGmsgrange'):
                                    gt = 1
                                    
                        else:
                            gt = 1
                                                                
        # Gate it to Rf port when source station was heard
 
        if gt <> 0:
            rxp = dixlibsql.GetRfPort(msgdest)

            if rxp >= 0:
                axg = [ax[1][0], ax[1][1], [['TCPIP', 0], [cvars.get('genCFGcall'), 1]], ax[1][3]]                        
                gts = dixlibax25.vir2txt(axg)
                radioports[rxp].sendgate('}' + gts)
                dixlibsql.airgatedaddrecord(rxp, gts)            

    # Message input queue Queue.Empty, 
    
    # Remember incoming mesages for 5 min (300 sec)
    wlst = {}
    t = time.time()
        
    for k, v in dupls.iteritems():
        if t - v < 300:
            wlst[k] = v

    dupls = wlst
    
    return 0



def CmdNorm(cmd):
    s = cmd.upper()

    cmdlst = ['DATE', 'DX', 'HELP', 'INFO', 'OWNER', 'PORTS', 'TIME', 'TYPE', 'UPTIME', 'VERSION']
    cmdlst += ['APRSD', 'APRSH', 'APRSM', 'APRSO', 'APRSP', 'APRSS', 'APRST', 'PING?', 'IGATE?']

    n = 0
    w = ''

    for p in cmdlst:
        if p.find(s) == 0:
            n += 1
            w = p

    return (n, w)
        
