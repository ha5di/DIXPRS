#! /usr/bin/python

####################################################
# APRS digipeater and gateway for amateur radio use
#
# (C) HA5DI - 2012
#
# http://sites.google.com/site/dixprs/
####################################################

import  os
import  sys
import  time
import  Queue
import  random
import  multiprocessing
import  platform
import  getopt
import  signal 
import  socket
import  binascii

import  dixpcommon
import  dixpigate
import  dixpagwpe
import  dixpkiss
import  dixprscfg
import  dixprscommon
import  dixlibaprs
import  dixdrvudp
import  dixlibsql
import  dixlibax25
import  dixlibgeo
import  dixlibmsg
import  dixpwebserver

from dixlibcommon import *
from dixpcommon import radioports
           
###############################################################################	
# Functions definitions
###############################################################################	

def usage():
    
    print
    print "Available command line switches:"
    print
    print "dixprs -v or --version"
    print
    print "dixprs -c <configfile> or dixprs --config=<configfile>"
    print
    print "Visit https://sites.google.com/site/dixprs/ for more information"
    print
    return
    
    
def prt():
    return time.strftime("%H:%M:%Sz", time.gmtime())

def emsg(msg, mode):
    if mode == 1:
        print "\nError:   " + msg
        
    elif mode == 0:
        print "\nWarning: " + msg

    else:
        print "\nMessage: " + msg
        
    return

def OsSignalHandler(signum, frame):
    global OsSignal
    print "SIGNUM", signum
    OsSignal = signum
        
if __name__ == '__main__':
    multiprocessing.freeze_support()
    OsSignal = 0

    # Check Python version
    v = platform.python_version_tuple()

    if v[0] <> '2' or v[1] < '6':
        print
        print '*** Error: your Python version (' +  platform.python_version() + ') is incompatible'
        print
        sys.exit(-1)

    # Check system type
    
    isunix = False
    
    if platform.uname()[0] == 'Linux':
        isunix = True
             
    #################################################
    # Default base parameters
    #################################################

    sysCFGcfgf = os.path.dirname(sys.argv[0]) + "/config.txt"
    genCFGspol = ''

    #################################################
    # Process command line switches
    #################################################

    if len(sys.argv) > 1:
        try:
            opts, args = getopt.getopt(sys.argv[1:], "hvc:", ["help", "version", "config=","multiprocessing-fork"])

        except:
            print "\nUnknown command line option"
            print
            sys.exit(-1)

        for o, a in opts:
            if o in ("-v", "--version"):
                print "\n" + dixprscommon.version + ' (' + dixprscommon.versdat + ') - (c) HA5DI'
                print
                sys.exit(-1)

            elif o in ("-h", "--help"):
                usage()
                sys.exit(-1)
                                                              
            elif o in ("-c", "--config"):
                sysCFGcfgf = a
                
            else:
                print "\nUnhendled option"
                print
                sys.exit(-1)

    #################################################

    print
    print "*** " + dixprscommon.version + " - " + dixprscommon.versdat + " - (pid=%s)" % (os.getpid())
    print
    
    #################################################
    # Initialize variables
    ################################################# 

    pigate = None
    pwebsr = None
    
    cvars.put('genCFGstat', 'TST')
    cvars.put('sysVARstart', time.gmtime())
    cvars.put('genCFGmetric', True)
    cvars.put('igwSTATrescnt', 0)

    igwstat = -1
    
    #################################################
    # Read configuration file
    #################################################

    # Open config file

    cfg = dixprscfg.readcfg(sysCFGcfgf)

    if len(cfg) == 0:
        emsg("Can't open configuration file '%s'" % (sysCFGcfgf), 1)
        print
        sys.exit(1)

    #------------------------------------------------   
    # GENERAL configuration settings
    #------------------------------------------------

    sect = dixprscfg.getcfgsection(cfg, 'GENERAL')[0]

    if len(sect) == 0:
        emsg("No GENERAL configuration found", 1)
        sys.exit(1)
        
    # Mandatory settings

    try:
        p = sect['CALLSIGN'].upper()
        cvars.put('genCFGcall', p)

        p = sect['LONGITUDE']
        cvars.put('genCFGlong', float(p))

        p = sect['LATITUDE']
        cvars.put('genCFGlati', float(p))
        
    except KeyError:
        emsg("Mandatory GENERAL configuration item missing", 1)
        sys.exit(1)

    # Optional settings

    try:
        genCFGbcntxt = sect['BCNTXT']
    except KeyError:
        genCFGbcntxt = "%v"

    try:
        genCFGspol = sect['SPOOL']
    except KeyError:
        pass
        
    try:
        p = sect['OWNER']
        cvars.put('genCFGowner', p)
    except KeyError:
        cvars.put('genCFGowner', '')
       
    try:
        p = sect['SYMBOL']
        if len(p) == 2:
            cvars.put('genCFGsymb', p)
    except KeyError:
        cvars.put('genCFGsymb', "S#") 
    
    try:
        p = sect['ASL']
        cvars.put('genCFGasl', int(p))
    except (KeyError, ValueError):
        cvars.put('genCFGasl', -99999.9)    

    try:
        p = sect['BCNTIME']
        v = int(p)
        if v < 15:
            v = 15
        cvars.put('genCFGbtim', v)
    except (KeyError, ValueError):
        cvars.put('genCFGbtim', 30)    

    try:
        p = sect['UDPBASE']
        cvars.put('genCFGudpbase', int(p))
    except KeyError:
        cvars.put('genCFGudpbase', dixprscommon.udpbase)    
                 
    try:
        cvars.put('genCFGmetric', dixprscfg.yesno(sect['METRIC']))
    except KeyError:
        pass

    try:
        p = sect['LOCALHOPS']
        cvars.put('genCFGlocalhops', int(p))
    except (KeyError, ValueError):
        cvars.put('genCFGlocalhops', 2)              

    try:
        p = sect['MSGRANGE']
        cvars.put('genCFGmsgrange', float(p))
    except  (KeyError, ValueError):
        cvars.put('genCFGmsgrange', None)    
        
    #------------------------------------------------   
    # ISGW configuration settings
    #------------------------------------------------

    cvars.put('igwCFGhost', None)

    try:
        sect = dixprscfg.getcfgsection(cfg, 'ISGW')[0]
    except IndexError:
        sect = []
        
    if len(sect) == 0:
        emsg("No ISGW configuration found, ISGW disabled", 0)

    else:

        # Mandatory settings
        
        try:
            p = sect['HOST']
            cvars.put('igwCFGhost', p)
            
        except KeyError:
            emsg("Mandatory ISGW configuration item missing", 1)
            sys.exit(1)

        # Optional settings

        try:
            p = sect['PORT']
            cvars.put('igwCFGport', int(p))
        except KeyError:
            cvars.put('igwCFGport', 14580)

        try:
            p = sect['FILTER']
            cvars.put('igwCFGfilter', p)
        except KeyError:
            cvars.put('igwCFGfilter', 'r/@/150')

        cvars.put('igwCFGbtxt', '')
        try:
            p = sect['BCNTXT']
            cvars.put('igwCFGbtxt', p)
        except KeyError:
            cvars.put('igwCFGbtxt', genCFGbcntxt)
            
    #------------------------------------------------   
    # WEB server configuration settings
    #------------------------------------------------

    cvars.put('webCFGport', None)

    try:
        sect = dixprscfg.getcfgsection(cfg, 'WEBSERVER')[0]
    except IndexError:
        sect = []
        
    if len(sect) == 0:
        emsg("No WEB server configuration found, WEB server disabled", 0)

    else:

        # Mandatory settings
        
        try:
            p = sect['PORT']
            cvars.put('webCFGport', int(p))
        except (KeyError, ValueError):
            emsg("Mandatory WEB server configuration item missing or faulty", 1)
            sys.exit(1)

        # Optional settings none


    #------------------------------------------------   
    # Radio configuration settings
    #------------------------------------------------

    sect = dixprscfg.getcfgsection(cfg, 'RADIO')
     
    for p in sect:
        radioports.append(dixpcommon.RADIOPORT())    
        ix = len(radioports) - 1   
        
        # System configuration

        radioports[ix].prtid = "%d" % (ix) 
    
        radioports[ix].udpmn = cvars.get('genCFGudpbase')
        radioports[ix].udpgw = cvars.get('genCFGudpbase') + 1
        radioports[ix].udptx = cvars.get('genCFGudpbase') + ix + 2    
        radioports[ix].axcal = cvars.get('genCFGcall') 
        radioports[ix].axdst = dixprscommon.dststrn
        
        # Optional parameters, port independent
        
        
        
        # TNC/modem settings
        
        xxctrl = {}        

        try:
            n = int(p['TXD'])
            if n >= 0 and n <= 255:                  
                xxctrl['TXD'] = n
        except (KeyError, ValueError):
            pass
        
        try:
            n = int(p['PPERSIST'])
            if n >= 0 and n <= 255:                  
                xxctrl['PPERSIST'] = n
        except (KeyError, ValueError):
            pass

        try:
            n = int(p['SLOTTIME'])
            if n >= 0 and n <= 255:                  
                xxctrl['SLOTTIME'] = n
        except (KeyError, ValueError):
            pass
        
        try:
            n = int(p['TXTAIL'])
            if n >= 0 and n <= 255:                  
                xxctrl['TXTAIL'] = n
        except (KeyError, ValueError):
            pass

        try:
            n = int(p['DUPLEX'])
            if n >= 0 and n <= 255:                  
                xxctrl['DULEX'] = n
        except (KeyError, ValueError):
            pass

        try:
            radioports[ix].ptton = dixprscfg.yesno(p['PTTON']) 
        except KeyError:
            pass

        try:
            radioports[ix].digen = dixprscfg.yesno(p['DIGIPEATER']) 
        except KeyError:
            pass

        try:
            radioports[ix].gsloc = dixprscfg.yesno(p['GATELOCAL']) 
        except KeyError:
            pass

        try:
            radioports[ix].gsdig = dixprscfg.yesno(p['GATEDIGI']) 
        except KeyError:
            pass

        try:
            radioports[ix].gtnws = dixprscfg.yesno(p['GATENWS']) 
        except KeyError:
            pass

        try:
            radioports[ix].gtbom = dixprscfg.yesno(p['GATEBOM']) 
        except KeyError:
            pass

        try:
            radioports[ix].aispp = float(p['SIGNALRATE']) 
        except (KeyError, ValueError):
            pass

        try:
            radioports[ix].tsglh = float(p['TRAFFICHIGH']) 
        except (KeyError, ValueError):
            pass

        try:
            radioports[ix].tsgll = float(p['TRAFFICLOW']) 
        except (KeyError, ValueError):
            pass

        try:
            radioports[ix].tsgid = float(p['TRAFFICDELAY']) 
        except (KeyError, ValueError):
            pass
            
        try:
            s = p['PHG'] 
            radioports[ix].phgbc = s
        except KeyError:
            pass
            
        try:
            s = p['RNG'] 
            radioports[ix].rngbc = int(s)
        except (KeyError, ValueError):
            pass

        try:
            s = p['DESCRIPTION'] 
            radioports[ix].pdesc = s
        except KeyError:
            radioports[ix].pdesc = 'No description'
 
        try:
            s = p['AXVIA'].upper() 
        except KeyError:
            s = 'WIDE1-1,WIDE2-2'
        radioports[ix].axvia = s

        try:
            s = p['WIDEN'].upper()
            w = s.split(',')
        except (KeyError, ValueError):
            w = ['WIDE1', 'WIDE2']
        radioports[ix].widen = w               

        try:
            s = p['BLACKLIST'].upper()
            w = s.split(',')
        except (KeyError, ValueError):
            w =  ['NOCALL', 'N0CALL']
        radioports[ix].blkls = w               
        
        radioports[ix].bcntx = ''
        
        try:
            radioports[ix].bcntx = p['BCNTXT']
        except KeyError:
            radioports[ix].bcntx = genCFGbcntxt

        try:
            udpcclst = [] 
            s = p['UDPCC']
            
            for q in s.split(','):
                w = dixprscfg.hostadr(q)
                
                if len(w) == 2:
                    udpcclst.append(w)
            
            radioports[ix].udpcc = udpcclst
             
        except (KeyError, ValueError):
            pass
            
        radioports[ix].udpcc = udpcclst
        
        # Port specific configuration
  
        ift = p['INTERFACE'].upper()

        if ift == 'KISS':
            
            # Mandatory parameters
            
            parsok = True
            
            try:
                s = p['PORT'] 
                xxprt = s
            except KeyError:
                parsok = False
                print "Missing port"
                
            try:
                s = p['SPEED'] 
                xxspd = int(s)
            except (KeyError, ValueError):
                parsok = False
                print "Missing speed"

            # Optional parameters
                                         
            # Start if mandatory parameters OK
                
            if parsok:
                radioports[ix].hwtyp = 'KISS'                    
                
                radioports[ix].hwcfg = (xxprt, xxspd, xxctrl)
                
                radioports[ix].start()
                
                while radioports[ix].drvpr.pid == None:
                    time.sleep(0.1)

                print "*** AIR%s  process started [%s] (pid=%s))" % (radioports[ix].prtid, radioports[ix].pdesc, radioports[ix].drvpr.pid)
                
                
            else:
                radioports.pop()
                print "Radio port configuration error"
            
        
        elif ift == 'AGWPE':
            # Mandatory parameters
            
            parsok = True
            
            try:
                s = p['PORT'] 
                xxport = int(s)
            except (ValueError, KeyError):
                parsok = False
                print "Missing port"

            try:
                s = p['HOST'] 
                xxhost = s
            except KeyError:
                parsok = False
                print "Missing host"

            try:
                s = p['CHANNEL'] 
                xxchannel = int(s)
            except (KeyError, ValueError):
                parsok = False
                print "Missing channel"

            # Start if mandatory parameters OK
                
            if parsok:
                radioports[ix].hwtyp = 'AGWPE'         
                chan = 0

                radioports[ix].hwcfg = (xxhost, xxport, xxchannel, xxctrl)
                radioports[ix].start()

                while radioports[ix].drvpr.pid == None:
                    time.sleep(0.1)                
                
                print "*** AIR%s  process started [%s] (pid=%s))" % (radioports[ix].prtid, radioports[ix].pdesc, radioports[ix].drvpr.pid)
                
            else:
                radioports.pop()
                print "Radio port configuration error"
  
        elif ift == 'AX25':
            # Mandatory parameters
            
            parsok = True
            
            try:
                xxaxdev = p['DEVICE'] 
            except KeyError:
                parsok = False
                print "Missing device"

            # Start if mandatory parameters OK
                
            if parsok:
                radioports[ix].hwtyp = 'AX25'                    

                radioports[ix].hwcfg = (xxaxdev, xxctrl)
                
                radioports[ix].start()
                
                while radioports[ix].drvpr.pid == None:
                    time.sleep(0.1)
                
                print "*** AIR%s  process started [%s] (pid=%s))" % (radioports[ix].prtid, radioports[ix].pdesc, radioports[ix].drvpr.pid)
                
            else:
                radioports.pop()
                print "Radio port configuration error"
 
        else:
            radioports.pop()
            print 'Unknown radio interface type: ' + p['INTERFACE']                 

    ###############################################################################	
    # Initialize variables
    ###############################################################################

    bcntm = time.time() + 60
    bcnph = 0

    tmcnt1sec = time.time()
    tmcnt1min = time.time() + 60            # first tick 1 minutes after start
    tmcnt15min = time.time() + 15 * 60      # first tick 15 minutes after start
    tmcnt1hr = time.time() + 60 * 60        # first tick 60 minutes after start
    tmcnt1day = time.time() + 24 * 60 * 60  # first tick 24 hours after start

    cnttm = random.randrange(0, 999, 50)
    divtm1 = 999
    divtm2 = 999

    ###############################################################################	
    # Initialize system
    ###############################################################################	

    #airindex['A0'] = 0

    ###############################################################################	
    # Initalize IGATE if enabled
    ###############################################################################	

    # Create IGATE object

    cvars.put('igtport', None)
    
    if cvars.get('igwCFGhost') <> None:
        # Setup UDP sending port (IGATE)

        igtport = dixlibaprs.IGPORT(cvars.get('genCFGudpbase') + 1)

        # Configure IGATE

        cvars.put('igtport', igtport)
        
        igtport.axhdr = cvars.get('genCFGcall') + '>' + dixprscommon.dststrn
        igtport.srvpr = cvars.get('igwCFGport')
        igtport.srvfl = cvars.get('igwCFGfilter')
        
        # Substitute @
        
        if igtport.srvfl.find('@') >= 0:
            igtport.srvfl = igtport.srvfl.replace('@', "%0.4f/%0.4f" % (cvars.get('genCFGlati'), cvars.get('genCFGlong')))

        pigate = multiprocessing.Process(target=dixpigate.procmain, args=(cvars.get('genCFGudpbase'), \
        cvars.get('igwCFGhost'), cvars.get('igwCFGport'), cvars.get('genCFGcall'), igtport.srvfl, \
        dixprscommon.version))    
        pigate.start()
        
        while pigate.pid == None:
            time.sleep(0.1)
        
        print "*** IGATE process started [host=%s, port=%d] (pid=%s)" % (cvars.get('igwCFGhost'), cvars.get('igwCFGport'),  pigate.pid)

    # Setup UDP listening port
    
    mainsocrx = dixdrvudp.UDPRx(cvars.get('genCFGudpbase'))
    mainsocrx.settimeout(0.01)
       
    # Setup beacon text
    if igtport <> None:
        s = cvars.get('igwCFGbtxt').strip()
        
        if s == '':
            s = dixprscommon.version
        else:
            s.replace('%v', dixprscommon.version)
                   
        igtport.bcntx = dixlibaprs.MkPosRep(-1, s)
        
    for i in range(len(radioports)):
        s = radioports[i].bcntx.strip()
        
        if s == '':
           s = dixprscommon.version
        else:
            s.replace('%v', dixprscommon.version)          
              
        radioports[i].bcntx = dixlibaprs.MkPosRep(i, s)        

    # Start WEB Server
    
    dpar = {}
    dpar['mycall'] = cvars.get('genCFGcall')

    dpar['long'] = cvars.get('genCFGlong')
    dpar['lati'] = cvars.get('genCFGlati')

    dpar['version'] = dixprscommon.version
    dpar['versdat'] = dixprscommon.versdat 
    dpar['owner'] = cvars.get('genCFGowner')
    dpar['metric'] = cvars.get('genCFGmetric')
    dpar['localhops'] = cvars.get('genCFGlocalhops')
    
    dprt = []
    
    for p in radioports:
        dprt.append([p.prtid, p.pdesc])
        
    dpar['ports'] = dprt        
                    
    if cvars.get('webCFGport') <> None:
        pwebsr = multiprocessing.Process(target=dixpwebserver.procmain, args=(cvars.get('webCFGport'), dpar))
        pwebsr.start()
        print "*** WEBSR process started [port=%d] (pid=%d)" % (cvars.get('webCFGport'), pwebsr.pid)        


    # Start sql system
    dixlibsql.start()

    # Cleanup sql database
    dixlibsql.DbDatPurge()   
    dixlibsql.DbTmpPurge()
    dixlibsql.DbVacuum()
    
    dixlibaprs.StatusUpdate(dixprscommon.version + " up and running")
    dixlibaprs.StatusSend()

    signal.signal(signal.SIGTERM, OsSignalHandler)

    print

    #######################################################
    # Main program loop
    #######################################################

    while OsSignal == 0:
        try:
                
            ###############################################
            # Process received UDP packets
            ###############################################

            try:
                w = mainsocrx.receive()
            except socket.error:
                pass          
                    
            if w <> None:
                #if w[1][0] == '127.0.0.1' and len(w[0]) > 4:
                if len(w) > 4:

                    # Received data packet from IGATE
                    if w[0:2] == 'RI' and igtport <> None:
                        igtport.putudpraw('R' + w[3:])
 
                    # Received status packet from IGATE
                    elif w[0:2] == 'SI' and igtport <> None:
                        v = w[3:].split('|')
                        st = int(v[0])                        
                        nr = int(v[2])

                        igtport.srvid = v[1]
                        
                        if igwstat < 0 and st == 9:
                            igwstat = 9
                            
                            dixlibaprs.StatusUpdate("Connected to %s count %d/%d" % (igtport.srvid, nr, cvars.get('igwSTATrescnt')))
                            dixlibaprs.StatusSend()

                            igtport.connr = nr
                        
                        elif igwstat == 9 and st <> 9:
                            igwstat = -1
                            igtport.srvid = ''
                            
                            dixlibaprs.StatusUpdate("Server connection lost")
                            dixlibaprs.StatusSend()
                            
                    # Received packet from radio
                    elif w[0] == 'R' or w[0] == 'S': 
                        # Enqueue received frames to radio port object
                        for i in range(0, len(radioports)):
                            if radioports[i].prtid == w[1]:
                                radioports[i].rxenqueue(w[0] + w[3:])
                                break
                            

            ###############################################
            # Process frames received via air interfaces
            ###############################################
            
            for airprt in range(0, len(radioports)):
                airtxt = radioports[airprt].receive()
                
                if airtxt <> '':

                    #---------------------------------------
                    # Process frames from input queue
                    #---------------------------------------
                                
                    airfrm = dixlibax25.txt2vir(airtxt)
            
                    if len(airfrm) == 4 and len(airfrm[3]) > 1:

                        #---------------------------------------
                        # Extract frame properties
                        #---------------------------------------
                        
                        hops = dixlibax25.GetHops(airfrm)
                            
                        # Check sender validity            
                        illegal = dixlibax25.IsInvalidCall(airfrm[0])

                        airpos = None
                        airdis = None
                                                
                        if dixlibaprs.IsPosition(airfrm):
                            pos = dixlibaprs.GetPosition(airfrm)

                            # Is position valid in received frame?
                            if len(pos) == 2 and pos <> (0, 0):
                                airpos = pos 
                                airdis = dixlibgeo.qradist(airpos, (cvars.get('genCFGlati'), cvars.get('genCFGlong')))                              
                                dixlibsql.putdbpos(airfrm[0], pos, airdis)                                                            

                        # Add received frame to hops database
                        dixlibsql.AddRfHeard(airfrm[0], airprt, hops)
                        
                        # Add received frame to heard database

                        hdr = ''
                        dti = -1
                        inf = ''
                        
                        idx = airtxt.find(':')
                        
                        if idx > 0:
                            hdr = airtxt[:idx]         
                            
                        try:
                            dti = ord(airtxt[idx + 1])                                           
                        except:
                            pass    

                        try:                            
                             inf = binascii.b2a_base64(airtxt[idx + 1:])
                        except:
                            pass                                                         
                                                
                        if airpos == None:
                            dixlibsql.AddRfHeardList(airfrm[0], airprt, hops, (0, 0), -9999.9, hdr, dti, inf)
                        else:
                            if airdis == None:
                                dixlibsql.AddRfHeardList(airfrm[0], airprt, hops, airpos, -9999.9, hdr, dti, inf)
                            else:
                                dixlibsql.AddRfHeardList(airfrm[0], airprt, hops, pos, airdis, hdr, dti, inf)
                                                         
                        # Get last known position from database if no posit in received frame
                        if airpos == None:
                            pos = dixlibsql.getdbpos(airfrm[0])
                           
                            if len(pos) == 2 and airpos <> (0, 0):
                                airpos = pos 
                                
                                
                        # Calculate distance on last known posit if no actual
                        if airdis == None and airpos <> None:
                            airdis = dixlibgeo.qradist(airpos, (cvars.get('genCFGlati'), cvars.get('genCFGlong')))

                        # Is it heard directly? 
                        airdir = dixlibax25.IsDirect(airfrm)                        

                        
                        #---------------------------------------
                        # Digipeating
                        #---------------------------------------

                        blklst = radioports[airprt].blkls

                        while True:
                            # Is digipeating anabled?
                            if not radioports[airprt].digen:
                                break                     
                            
                            # Do not digipeat frames from illegal sender
                            if illegal:
                                break

                            # Check number of digis in via
                            if len(airfrm[2]) == 0 or len(airfrm[2]) > 5:
                                break

                            dflg = True
                            
                            # Check blacklisted digis already passed
                            for p in airfrm[2]:
                                # Not yet repeated
                                if p[1] == 0:
                                    continue

                                if blklst.count(p[0]) <> 0:
                                    dflg = False
                                    break

                            # Stop checking if blacklisted via                
                            if not dflg:
                                break

                            # Check blacklisted sender
                            if blklst.count(airfrm[0]) <> 0:
                                dflg = False

                            # Stop checking if blacklisted sender
                            if not dflg:
                                break

                            
                            # Find unused digi
                            for i in range(0, len(airfrm[2])):

                                # Build output frame
                                xvia = airfrm[2][:i]
                                    
                                # Already repeated
                                if airfrm[2][i][1] <> 0:
                                    continue

                                # Check our alias list
                                if [cvars.get('genCFGcall'), 'RELAY'].count(airfrm[2][i][0]) <> 0:
                                    # Add ourself to digi list
                                    xvia.append([cvars.get('genCFGcall'), 1])

                                    # Add rest of digis

                                    for j in range(i+1, len(airfrm[2])):
                                        xvia.append(airfrm[2][j])
                                        
                                    axtx = [airfrm[0], airfrm[1], xvia, airfrm[3]]
                                    radioports[airprt].senddigi(dixlibax25.vir2txt(axtx))
                                    break

                                else:
                                    # Check WIDEn-n
                                    w = airfrm[2][i][0].split('-')

                                    if len(w) > 1:
                                        try:
                                            ssid = int(w[1])
                                        except ValueError:
                                            ssid = 0
                                            
                                    else:
                                        ssid = 0

                                    digi = w[0]

                                    if ssid == 0:
                                        break

                                    if radioports[airprt].widen.count(digi) == 0:
                                        break

                                    # Add ourself to digi list
                                    xvia.append([cvars.get('genCFGcall'), 1])
                                    
                                    # Add WIDE-n digi if not counted down
                                    if ssid > 1:
                                        xvia.append(["%s-%d" % (digi, ssid - 1), 0])

                                    # Add rest of digis

                                    for j in range(i+1, len(airfrm[2])):
                                        xvia.append(airfrm[2][j])

                                    axtx = [airfrm[0], airfrm[1], xvia, airfrm[3]]
                                    radioports[airprt].senddigi(dixlibax25.vir2txt(axtx))
                                    break
                                    
                                
                            # Make shure it terminates
                            break
                        
                        # End of while, make shure it terminates

                        #---------------------------------------
                        # Process general queries
                        #---------------------------------------

                        if airfrm[3][0] == '?' and not illegal:
                            if airfrm[3][:6] == '?APRS?':
                                radioports[airprt].sendmy(radioports[airprt].bcntx)
                            
                            elif airfrm[3][:7] == '?IGATE?':
                                s = '<IGATE,' + dixlibaprs.mkcaptxt(airprt)
                                radioports[airprt].sendmy(s)
                                
                            #elif airfrm[3][:4] == '?WX?':
                            
                        #---------------------------------------
                        # Process messages received via radio
                        #---------------------------------------
                        
                        # Unwrap encapsulated frames
                        
                        xfrm = airfrm
                        
                        while True:
                            try:
                                if xfrm[3][0] <> '}':
                                    break
                                        
                                xfrm = dixlibax25.txt2vir(xfrm[3][1:])       
                            except IndexError:
                                break                   

                        # Check unwrapped frame for message
                        try:
                            if xfrm[3][0] == ':':             
                                destcal = dixlibmsg.GetDestcall(xfrm[3])
                                destpos = dixlibsql.getdbpos(destcal)
                                dixlibmsg.msgproc((airprt, xfrm))
                            
                                #print "MSG IN RF:", airprt, xfrm
                        except IndexError:
                            pass
                            
                        #---------------------------------------
                        # Print received frame on console
                        #---------------------------------------
                        if True:
                            s = prt() + " AIR%c " % (radioports[airprt].prtid)
                            

                            if airdir:
                                s += '***'
                            else:
                                s += "[%d]" % (hops)

                            if illegal:
                                s += ' ! '
                            else:
                                s += ' > '

                            if airdis <> None:
                                wds = "(%10s) " % (dixlibgeo.fmtdist(airdis, cvars.get('genCFGmetric')))
                            else:
                                wds = 13 * ' '
                                
                            s += wds + airtxt

                            print s


            ###############################################
            # Process frames received via Internet Gateway
            ###############################################

            if igtport <> None:
                while True:
                    igttxt = igtport.receive()
                    #print "###", igttxt
                    if len(igttxt) == 0:
                        break
                            
                    else:         
                        #---------------------------------------
                        # Process frames from input queue
                        #---------------------------------------                                                                    
                        
                        igtfrm = dixlibax25.txt2vir(igttxt)
                
                        if len(igtfrm) == 4 and len(igtfrm[3]) > 1: 
                            if dixlibaprs.IsPosition(igtfrm):
                                pass
                                #print "POSITION:", igtfrm
    
                            #---------------------------------------
                            # Add sender to net connected list
                            #---------------------------------------
    
                            if isnetconnected(igtfrm):
                                dixlibsql.airaddstnnetlist(igtfrm[0])                    
                                  
                            #---------------------------------------
                            # Send positions if sender was gated 
                            #---------------------------------------

                            if dixlibsql.IsGatedFrom(igtfrm[0]): 

                                if dixlibaprs.IsPosition(igtfrm):
                                    nrport = dixlibsql.GetGatedPort(igtfrm[0])
                                    
                                    if nrport >= 0:
                                        radioports[nrport].sendgate('}' + igttxt)
                               
                            #-----------------------------------------------
                            # Process messages received via Internet Gateway
                            #-----------------------------------------------
    
                            if igtfrm[3][0] == ':':
                                destcal = dixlibmsg.GetDestcall(igtfrm[3])
                                destpos = dixlibsql.getdbpos(destcal)
                                dixlibmsg.msgproc((-1, igtfrm))
                                
                                #print "MSG IN GW:", -1, igtfrm

                            #---------------------------------------
                            # Check NWS/BOM WX objects 
                            #---------------------------------------

                            elif igtfrm[3][0] == ';':
                                
                                if igtfrm[2][1][0] == 'WXSVR-AU':
                                    for pwx in radioports:
                                        if pwx.gtbom:
                                            pwx.sendgate('}' + igttxt)
                                            
                                elif igtfrm[2][1][0][-3:] == '-WX':
                                    for pwx in radioports:
                                        if pwx.gtnws:
                                            pwx.sendgate('}' + igttxt)
                        
            ###############################################
            # Process frames sent via radio interfaces
            ###############################################

            for port in range(0, len(radioports)):
                sntlst = []
                
                snt = radioports[port].sent()
                                         
                if snt <> '':
                    sntlst.append(('LOCL', snt))  
                    dixlibsql.addsentlist(port, 0)
                    
                    # Gate to IGATE if gatesent enabled

                    if radioports[port].gsloc:
                        if igtport <> None:
                            igtport.send(snt)

                snt = radioports[port].sentdigi()     

                if snt <> '':
                    sntlst.append(('DIGI', snt))
                    dixlibsql.addsentlist(port, 1)
                    
                    # Gate to IGATE if gatesent enabled

                    if radioports[port].gsdig:
                        if igtport <> None:
                            igtport.send(snt)

                snt = radioports[port].sentgate()     

                if snt <> '':
                    sntlst.append(('GATE', snt))
                    dixlibsql.addsentlist(port, 2)
                                        
                    # Gate to IGATE if gatesent enabled

                    #if radioports[port].gsdig:
                    #    if igtport <> None:
                    #        igtport.send(snt)
                                            
                # Display on console
                
                for sent in sntlst:
                
                    print prt() + ' AIR%c         <- %s    %s' % (radioports[port].prtid, sent[0], sent[1])
                    fr = dixlibax25.txt2vir(sent[1])

                    if len(fr) == 4:
                        pvlst = ''

                        for pv in fr[2]:
                            pvlst += pv[0]

                            if pv[1] <> 0:
                                pvlst += '*'

                            pvlst += ' '

                        pvlst = pvlst.strip()

            ###############################################
            # Process frames sent via IGT interfaces
            ###############################################
            
            if igtport <> None:
                sent = igtport.sent()
                    
            tm = time.time()

    
            ###################################
            # Process incoming spool
            ###################################                
    
            if genCFGspol <> '':
                try:
                    lst = os.listdir(genCFGspol)
                    lst.sort()
                
                    for p in lst:
                        if  p[-3:].upper() == 'PKT':
                            fn = genCFGspol + '/' + p
                            time.sleep(0.01)
                     
                            try:
                                fp = open(fn)
                                w = fp.readlines()
                                fp.close()
                            except IOError:
                                continue
                                
                            os.remove(fn)
        
                            if len(w) >= 2:
                                if len(w[1]) > 10:
                                    
                                    # Send it to GW?
                                    if w[0].find('G') >= 0 or w[0].find('*') >= 0:
                                        if igtport <> None:
                                            igtport.send(w[1].strip())
                                        
                                    for k in range(0,len(radioports)):
                                        if w[0].find(radioports[k].prtid) >= 0 or w[0].find('*') >= 0:
                                            radioports[k].send(w[1].strip())
        
                        elif p[-3:].upper() == 'MYP':
                            fn = genCFGspol + '/' + p
                            fp = open(fn)
                            w = fp.readlines()
                            fp.close()
                            time.sleep(0.01)
                            os.remove(fn)
        
                            if len(w) >= 2:
                                if len(w[1]) > 10:
                                    
                                    # Send it to GW?
                                    if w[0].find('G') >= 0 or  w[0].find('*') >= 0:
                                        if igtport <> None:
                                            igtport.sendmy(w[1].strip())
                                    
                                    for k in range(0,len(radioports)):
                                        if w[0].find(radioports[k].prtid) >= 0 or w[0].find('*') >= 0:
                                            radioports[k].sendmy(w[1].strip())
                                        
          
                except OSError:
                    pass
                    
            ###############################################
            # Send beacon
            ###############################################
            
            if tm >= bcntm:
                if bcnph < len(radioports):
                    if radioports[bcnph].bcntx <> None:
                        radioports[bcnph].sendmy(radioports[bcnph].bcntx)            
                    radioports[bcnph].sendmy('<IGATE,' + dixlibaprs.mkcaptxt(bcnph)) 
                    
                    bcnph += 1
                    bcntm += 60

                    
                else:
                    bcnph = 0
                    bcntm += cvars.get('genCFGbtim') * 60 - len(radioports) * 60

                    if igtport <> None: 
                        if igtport.bcntx <> None:                        
                            igtport.sendmy(igtport.bcntx)
                            igtport.sendmy('<IGATE,' + dixlibaprs.mkcaptxt(-9))

            ###############################################
            # Timed actions
            ###############################################

            # 1 sec tick
            elif tm > tmcnt1sec:
                tmcnt1sec += 1.0

                for p in radioports: 
                    if not p.tsgtq.empty():                 
                        p.dequeuegate()
                    
                    #r = p.trload()                     
                    #print p.tsgtq.empty(), p.tsgtm, p.tsgtd, "%s RX:%0.1f%s TX:%0.1f%s  -> %0.1f%s" % (p.prtid, r[0] * 100.0, '%', r[1] * 100.0, '%', (r[0] + r[1]) * 100, '%')
                #print
                
                ###################################
                # Process outgoing message queue
                ###################################

                # Handle ack/rej
                try:
                    ack = ackqueue.get(False)
                    dixlibsql.msgack(ack)
                        
                except Queue.Empty:
                    pass

                # Handle new outgoing messages
                try:
                    msgout = msgqueue.get(False)
                    dixlibsql.msgadd([msgout[0], msgout[1], msgout[2]])

                except Queue.Empty:
                    pass

                uui = dixlibsql.msggetnext()

                if uui <> []:
                    dixlibmsg.SendMy2Autoport(uui[0], uui[2])
                
                
            # 1 minute tick
            elif tm > tmcnt1min:
                tmcnt1min += 60.0
            
                # Check process alive status
                
                # Check Igate process if exists                
                if pigate <> None:
                    if pigate.is_alive() == False:
                        pass
                                                
                # Check radio drivers
                for p in radioports:
                    # Clean traffic database
                    p.dbclean()
                    
                    if p.drvpr <> None:
                        if p.drvpr.is_alive() == False:
                            pass
                            
            # 15 minutes tick
            elif tm > tmcnt15min:
                tmcnt15min += 900.0           
                
                dixlibsql.DbTmpPurge()


                # Send telemetry to ISGW if enabled
                if pigate <> None:
                    tlmw = dixlibsql.GetTlmData(0)
                    tlms = 'T#%03d,%d,%d,%d,%d,%d,' % (cnttm, tlmw[0], tlmw[1], tlmw[2], tlmw[3], tlmw[4])
                    tlmu = ':%-9s:UNIT.pkt/15m,pkt/15m,stn/15m,stn/15m,pkt/15m' % (cvars.get('genCFGcall'))

                    if cvars.get('webCFGport') == None:
                        tlms += '0'
                        tlmu += ',off'
                    else:
                        tlms += '1'
                        tlmu += ',on'

                    if radioports[0].gtnws:
                        tlms += '1'
                        tlmu += ',on'
                    else:
                        tlms += '0'
                        tlmu += ',off'
                        
                    if radioports[0].gtbom:
                        tlms += '1'
                        tlmu += ',on'
                    else:
                        tlms += '0'
                        tlmu += ',off'
                        
                    tlms += '00000'                                                
                                                
                    igtport.sendmy(tlms)
                    cnttm = (cnttm + 1) % 1000                                     

                    # Send telemetry definitions in every 60 minutes
                    if divtm1 > 3:
                        igtport.sendmy(':%-9s:PARM.RxTot,RxDir,RxTot,RxDir,TxTot,WEB,NWS,BOM' % (cvars.get('genCFGcall')))
                        igtport.sendmy(':%-9s:EQNS.0,1,0,0,1,0,0,1,0,0,1,0,0,1,0' % (cvars.get('genCFGcall')))
                        igtport.sendmy(tlmu)

                        divtm1 = 0

                    divtm1 += 1

            # 1 hour tick
            elif tm > tmcnt1hr:
                tmcnt1hr += 3600.0

                dixlibsql.DbDatPurge()                
                    
            # 1 day tick
            elif tm > tmcnt1day:
                tmcnt1day += 86400.0
                
                
            # Subprocess health check
            
            if pigate <> None:
            
                if not pigate.is_alive():
                    pigate.terminate()
                    
                    pigate = multiprocessing.Process(target=dixpigate.procmain, args=(cvars.get('genCFGudpbase'), \
                    cvars.get('igwCFGhost'), cvars.get('igwCFGport'), cvars.get('genCFGcall'), cvars.get('igwCFGfilter'), \
                    dixprscommon.version))    
                    pigate.start()
                    cvars.put('igwSTATrescnt', cvars.get('igwSTATrescnt') + 1)

                    dixlibaprs.StatusUpdate("Pigate process restarted")
                    dixlibaprs.StatusSend()                    
                    
                    print "*** Restarted PIGATE process"
                                                   
        except KeyboardInterrupt:
            OsSignal = -1

            
    #######################################################
    # Main program loop terminated
    #######################################################

    if OsSignal < 0:
        s = "Ctrl/C"
    else:
        s = "Signal %d" % (OsSignal)         

    print
    print
    print "%s received, shutting down" % (s)
    print
    
    dixlibaprs.StatusUpdate('Shutting down')
    dixlibaprs.StatusSend()

    time.sleep(5.0)

    # Close listening port
    mainsocrx.close()


    # Close Rf ports
    for p in radioports:
        p.stop()
        print "AIR%s  process stopped [%s]" % (p.prtid, p.pdesc)
        
    # Close sql database
    dixlibsql.finish()

    # Close Internet Gateway if enabled

    if pigate <> None:
        pigate.terminate()
        while pigate.is_alive():
            time.sleep(0.01)

        print 'IGATE process stopped'
        
    # Close WEB Server if enabled

    if pwebsr <> None:
        pwebsr.terminate()
        while pwebsr.is_alive():
            time.sleep(0.01)

        print 'WEBSR process stopped'
        
    print
    print
    	
