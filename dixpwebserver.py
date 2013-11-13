#! /usr/bin/python

####################################################
# APRS digipeater and gateway for amateur radio use
#
# (C) HA5DI - 2012
#
# http://sites.google.com/site/dixprs/
####################################################

import  time
import  string
import  platform
import  sqlite3
import  sys
import  os

from wsgiref.simple_server import make_server  

import  dixlibsql
    
###############################################################################
#
# Main program
#
###############################################################################	

def webmain(environ, start_response):     
    t = time.time()
    
    global st
    global dp

    status = '200 OK'
    headers = [('Content-type', 'text/html')] 
    start_response(status, headers)
    
    s = environ['REQUEST_METHOD'] + '\n<b>' + environ['PATH_INFO'] + '</b>\n' + environ['QUERY_STRING'] 
       
    fp = open(os.path.dirname(sys.argv[0]) + '/dixp1.htm')
    w = fp.read(100000)
    fp.close()
    
    s = string.Template(w) 
    
    d = {}
    d['dixpar01'] = '<a href="http://aprs.fi/info/a/' + dp['mycall'] + '">' + dp['mycall'] + '</a>'
    d['dixpar02'] = dp['version'] + ' ' + dp['versdat']
    
    w = platform.uname()[0] + ' ' + platform.uname()[2] + ' (' + platform.uname()[4] \
        + '), Python ' + platform.python_version()
    d['dixpar03'] = w 
    
    w = "%0.4f" % (abs(dp['lati']))
    if dp['lati'] >= 0:
        w += 'N'
    else:
        w += 'S'
        
    w += " %0.4f" % (abs(dp['long']))
    if dp['long'] >= 0:
        w += 'E'
    else:
        w += 'W'

    d['dixpar04'] = w 
                    
    d['dixpar05'] = dp['owner']
    d['dixpar06'] = time.strftime("%d-%m-%Y %H:%M:%Sz", time.gmtime())
    d['dixpar07'] = time.strftime("%d-%m-%Y %H:%M:%Sz", st)
    
    uptd = (time.mktime(time.gmtime()) - time.mktime(st)) / 86400.0
    upth = (uptd - int(uptd)) * 24.0
    uptm = (upth - int(upth)) * 60.0
    w = "%d days %d hours %d mins" % (int(uptd), int(upth), int(uptm))
    d['dixpar08'] = w

    # Stations heard
    r = getposits()
    d['dixpar09'] = "%d" % (r)

    # Heard direct
    
    if len(dp['ports']) == 1:
        hrd = airgetdirect1h(0)

        if len(hrd) == 0:
            v = 'Nothing'
        else:
            v = ''
        
            for p in hrd:
                v += p + ' '
            
            v = v[:-1]    
    else:
        v = ''
        
        for i in range(0, len(dp['ports'])):
            hrd = airgetdirect1h(i)    
            print i, hrd
            
            if len(hrd) == 0:
                w = 'Nothing'
            else:
                w = ''
            
                for p in hrd:
                    w += p + ' '
                
                w = w[:-1]    
        
            if i <> 0:
                v += '<br><br>'
            
            v += "AIR%d - " % (i) + w
                               
    d['dixpar10'] = v    

    if len(dp['ports']) == 1:
        v = "%s" % (dp['ports'][0][1])
    else:            
        v = "AIR%s - %s" % (dp['ports'][0][0], dp['ports'][0][1])
    
        for i in range(1, len(dp['ports'])):
            v += "<br>AIR%s - %s" % (dp['ports'][i][0], dp['ports'][i][1])
        
    d['dixpar11'] = v

    dxlen = 2

    # DX 1h

    if len(dp['ports']) == 1:
        res1 = GetDx1h(dxlen, 0)        
 
        v = ''      

        for p in res1:         
            v += "%s %s %s<br>" % (p[0], fmttime(p[1]), fmtdist(p[3], dp['metric']))
    else:
        v = ''
        
        for i in range(0, len(dp['ports'])):
            res1 = GetDx1h(dxlen, i)        

            w = ''    
            
            if i <> 0 and len(dp['ports']) > 1:
                w = '<br>'  

            for p in res1:
                w += "AIR%d - %s %s %s<br>" % (i, p[0], fmttime(p[1]), fmtdist(p[3], dp['metric']))
            
            v += w
        
    d['dixpar13'] = v.encode('ISO-8859-2')

    # DX 24h
    if len(dp['ports']) == 1:
        res1 = GetDx24h(dxlen, 0)        

        v = ''      

        for p in res1:         
            v += "%s %s %s<br>" % (p[0], fmttime(p[1]), fmtdist(p[3], dp['metric']))

    else:
        v = ''
        
        for i in range(0, len(dp['ports'])):
            res1 = GetDx24h(dxlen, i)        

            w = ''    
            
            if i <> 0 and len(dp['ports']) > 1:
                w = '<br>'  

            for p in res1:
                w += "AIR%d - %s %s %s<br>" % (i, p[0], fmttime(p[1]), fmtdist(p[3], dp['metric']))
            
            v += w
        
    d['dixpar14'] = v.encode('ISO-8859-2')

    # DX Total
    if len(dp['ports']) == 1:
        res1 = GetDxTot(dxlen, 0)        

        v = ''      

        for p in res1:         
            v += "%s %s %s<br>" % (p[0], fmttime(p[1]), fmtdist(p[3], dp['metric']))

    else:
        v = ''
        
        for i in range(0, len(dp['ports'])):
            res1 = GetDxTot(dxlen, i)        

            w = ''    
            
            if i <> 0 and len(dp['ports']) > 1:
                w = '<br>'  

            for p in res1:
                w += "AIR%d - %s %s %s<br>" % (i, p[0], fmttime(p[1]), fmtdist(p[3], dp['metric']))
            
            v += w
        
    d['dixpar15'] = v.encode('ISO-8859-2')
    
    # Igate capabilities    
    if len(dp['ports']) == 1:
        v = igatetxt(0, dp['localhops'])
    else:
        v = ''

        for i in range(0, len(dp['ports'])):
            v += "AIR%d - %s<br>" % (i, igatetxt(i, dp['localhops']))  
        
    d['dixpar12'] = v
        
    # Creation time    
    d['dixpar99'] = "%0.3f" % (time.time() - t)
    
    v = s.safe_substitute(d)

    return [v]


def km2mi(v):
    return v * 0.621371192
    
def mi2km (v):
    return v / 0.621371192     

def fmtdist(v, mode):
    if mode:
        s = "%0.1f km" % (v) 
    else:
        s = "%0.1f mi" % (km2mi(v))
        
    return s 
    
def fmttime(tm):
    return time.strftime("%d-%m-%Y %H:%Mz", time.gmtime(tm))    
        
def getposits():        
    con = sqlite3.connect(os.path.dirname(sys.argv[0]) + '/dixprsdta.db')
    cur = con.cursor()
    
    cmd = 'SELECT count(stn) FROM posits'
    cur.execute(cmd)
    res = cur.fetchone()
    
    cur.close()
    con.close()
    
    if res == None:
        return 0
        
    return res[0]
              
# Get list of directly heard stations in last 1 hour

def airgetdirect1h(port):
    
    res = GetRfHeard(port, 0)
    
    lst = []    
    
    for p in res:
        lst.append(p[0].encode('ISO-8859-2'))
        
    return lst
    

def GetRfHeard(port, maxhops):
    con = sqlite3.connect(os.path.dirname(sys.argv[0]) + '/dixprstmp.db')
    cur = con.cursor()

    if port < 0:
        cmd = "SELECT stn, tm, min(hops) FROM heardrf WHERE tm>%f AND hops<=%d GROUP BY stn ORDER BY stn" % (time.time() - 3600.0, maxhops)
    else:        
        cmd = "SELECT stn, tm, min(hops) FROM heardrf WHERE tm>%f AND port=%d AND hops<=%d GROUP BY stn ORDER BY stn" % (time.time() - 3600.0, port, maxhops)
       
    cur.execute(cmd)
    res = cur.fetchall()
    
    cur.close()
    con.close()
    
    return res         


def GetDx1h(n, port):
    con = sqlite3.connect(os.path.dirname(sys.argv[0]) + '/dixprstmp.db')
    cur = con.cursor()
    
    if port < 0:
        cmd = "SELECT stn,tm,port,dist FROM heardlist WHERE tm>%f AND hops=0 AND dist>=0 GROUP BY stn ORDER BY dist DESC LIMIT %d" % (time.time() - 3600.0, n)
    else:
        cmd = "SELECT stn,tm,port,dist FROM heardlist WHERE tm>%f AND hops=0 AND dist>=0 AND port=%d GROUP BY stn ORDER BY dist DESC LIMIT %d" % (time.time() - 3600.0, port, n)
        
    cur.execute(cmd)   
    res = cur.fetchall()  
    
    cur.close()
    con.close()      
    return res      

def GetDx24h(n, port):
    con = sqlite3.connect(os.path.dirname(sys.argv[0]) + '/dixprsdta.db')
    cur = con.cursor()
    
    if port < 0:
        cmd = "SELECT stn,tm,port,dist FROM dxlst24h WHERE tm>%f ORDER BY dist DESC LIMIT %d" % (time.time() - 24 * 3600.0, n)
    else:
        cmd = "SELECT stn,tm,port,dist FROM dxlst24h WHERE tm>%f AND port=%d ORDER BY dist DESC LIMIT %d" % (time.time() - 24 * 3600.0, port, n)

    cur.execute(cmd)   
    res = cur.fetchall()     
    
    cur.close()
    con.close()   
    return res      


def GetDxTot(n, port):
    con = sqlite3.connect(os.path.dirname(sys.argv[0]) + '/dixprsdta.db')
    cur = con.cursor()    
    
    if port < 0:
        cmd = "SELECT stn,tm,port,dist FROM dxlsttot ORDER BY dist DESC LIMIT %d" % (n)
    else:
        cmd = "SELECT stn,tm,port,dist FROM dxlsttot WHERE port=%d ORDER BY dist DESC LIMIT %d" % (port, n)

    cur.execute(cmd)   
    res = cur.fetchall()     
    
    cur.close()
    con.close()  
    return res
    
    
def igatetxt(port, maxhops):
    con = sqlite3.connect(os.path.dirname(sys.argv[0]) + '/dixprstmp.db')
    cur = con.cursor()    

    s = ''

    cmd = "SELECT * FROM gatedlist WHERE tm>%f AND port=%d" % (time.time() - 3600.0, port)
    cur.execute(cmd) 
    res = cur.fetchall()

    s += "MSG_CNT=%d" % (len(res))    
    
    cmd = "SELECT stn, tm, min(hops) FROM heardrf WHERE tm>%f AND port=%d AND hops<=%d GROUP BY stn ORDER BY stn" % (time.time() - 3600.0, port, maxhops)
    cur.execute(cmd) 
    res = cur.fetchall()
    s += " LOC_CNT=%d" % (len(res))    

    cmd = "SELECT stn, tm, min(hops) FROM heardrf WHERE tm>%f AND port=%d AND hops=0 GROUP BY stn ORDER BY stn" % (time.time() - 3600.0, port)
    cur.execute(cmd) 
    res = cur.fetchall()
    s += " DIR_CNT=%d" % (len(res))    

    cmd = "SELECT stn, tm, min(hops) FROM heardrf WHERE tm>%f AND port=%d GROUP BY stn ORDER BY stn" % (time.time() - 3600.0, port)
    cur.execute(cmd) 
    res = cur.fetchall()
    s += " RF_CNT=%d" % (len(res))    
    
    cur.close()
    con.close()
    
    return s    


def procmain(webport, dpar):
    # Initialize variables 

    global st
    global dp
    
    dp = dpar

    st = time.gmtime()
    
    httpd = make_server('', webport, webmain)

    # Main program loop
    try:
    
    
        while True:
            httpd.handle_request()

    except KeyboardInterrupt:
        pass
    

    # ---- End of procmain
