#!/usr/bin/snimpy
#~ 
#~ Copyright (C) 2014 Orange
#~ 
#~ This software is distributed under the terms and conditions of the 'Apache-2.0'
#~ license which can be found in the file 'LICENSE.txt' in this package distribution 
#~ or at 'http://www.apache.org/licenses/LICENSE-2.0'. 
#~ 

#~ 
#~ Real Time Node Supervision 
#~ 
#~ Module name: Real Time Node Supervision - Agent
#~ Version:     1.0
#~ Created:     2014-06-27 by David Blaisonneau
#~ 
import pprint
import re
import redis 
import socket
import time
import sys
import signal

sending_interval = 10 #in second
history = 120
send_cpu = 0 # No method for the moment
send_mem = 0 # no method for the moment
send_net = 1
default_community =  "public"
rtns_ip = "172.20.113.170"
rtns_password = ""
pp = pprint.PrettyPrinter(indent=4)

list_only_net_idx = [
        10052,
        10054,
        10122,
        10124,
    ]

##
# Check arguments
##

if len(sys.argv)==3:
    remote_server = sys.argv[2]
    remote_server_community = default_community
elif len(sys.argv)==4:
    remote_server = sys.argv[2]
    remote_server_community = sys.argv[3]
else:
	print "Usage: ./rtns-agent-redis.py SNMP_NODE [SNMP_COMMUNITY]\n"
	raise SystemExit

##
# Prepare SNMP Client
##
exit
m = M(remote_server, remote_server_community, 2)

load("IF-MIB")
load("SNMPv2-MIB")

##
# Prepare hostname
##
hostname = re.sub("\..*", "", m.sysName)
t = str(int(time.time()*1000))

##
# Connect to REDIS
##

#~ r = redis.Redis({'host':rtns_ip, 'password':rtns_password})
r = redis.Redis(rtns_ip)

##
# Register in nodes_list
##
print "Add '%s' in nodes_list\n" % hostname
r.sadd('nodes_list',hostname)
print "Data to send:\n"

##
# Define functions
##

# Push data to Redis
def redPush( key, val):
    #~ print key+" = "+val
    r.lpush(key,val)
    r.ltrim(key, 0, history)

# Send Net data
if send_net:
    oldifVal={}
    re_clean = re.compile(r"[ /_\.]")
    re_swinet_Gig = re.compile('^(.*GigabitEthernet.+)')
    re_swinet_FortyGig = re.compile('^(FortyGigE.+)')
    re_swinet_Bridge = re.compile('^(Bridge-Aggregation\d+)')
    re_swinet_Vlan = re.compile('^(Vlan-interface\d+)')
    re_esxinet_vmnic = re.compile('^Device (vmnic\d+)')
    re_esxinet_linkaggregation = re.compile('^Link Aggregation (.*) on switch: vSwitch(\d+), load ')
    re_esxinet_vswitch = re.compile('^.*Virtual VMware switch: (.*)')
    re_esxinet_vif = re.compile('^Virtual interface: (vmk\d+)')
    re_hp_vc_d = re.compile('^HP VC Flex.*Module \d\.\d+ (d.+)$')
    re_hp_vc_X = re.compile('^HP VC Flex.*Module \d\.\d+ (X.+)$')
    re_hp_vc_lag = re.compile('^lag(\d+)')
    re_eth_if = re.compile('^eth(\d+)')
    re_br_if = re.compile('^br(\d+)')
    re_tap_if = re.compile('^tap(\d+)')
    re_foo_numbered = re.compile('^(.*)(\d+)$')
    def cleanName(name):
        return re_clean.sub('-', name)
        
    def getShortIfName(ifDescr):        
        if re_swinet_Gig.match(ifDescr):        
            return "net-GEth_"+cleanName(re_swinet_Gig.match(ifDescr).group(1))
        if re_swinet_FortyGig.match(ifDescr):        
            return "net-40GEth__"+cleanName(re_swinet_FortyGig.match(ifDescr).group(1))
        if re_swinet_Bridge.match(ifDescr):        
            return "net-bridge_"+cleanName(re_swinet_Bridge.match(ifDescr).group(1))
        if re_swinet_Vlan.match(ifDescr):        
            return "net-vlan_"+cleanName(re_swinet_Vlan.match(ifDescr).group(1))
        if re_esxinet_vmnic.match(ifDescr):        
            return "net-vmnic_"+cleanName(re_esxinet_vmnic.match(ifDescr).group(1))
        if re_esxinet_linkaggregation.match(ifDescr):        
            return "net-linkaggregation_"+cleanName(re_esxinet_linkaggregation.match(ifDescr).group(1)+'-vSw'+re_esxinet_linkaggregation.match(ifDescr).group(2))
        if re_esxinet_vswitch.match(ifDescr):        
            return "net-vswitch_"+cleanName(re_esxinet_vswitch.match(ifDescr).group(1))
        if re_esxinet_vif.match(ifDescr):        
            return "net-vinterf_"+cleanName(re_esxinet_vif.match(ifDescr).group(1))
        if re_hp_vc_d.match(ifDescr):        
            return "net-VC-int_"+cleanName(re_hp_vc_d.match(ifDescr).group(1))
        if re_hp_vc_X.match(ifDescr):        
            return "net-VC-ext_"+cleanName(re_hp_vc_X.match(ifDescr).group(1))
        if re_hp_vc_lag.match(ifDescr):        
            return "net-VC-lag_"+cleanName(re_hp_vc_lag.match(ifDescr).group(1))
        if re_eth_if.match(ifDescr):        
            return "net-eth_"+cleanName(re_eth_if.match(ifDescr).group(1))
        if re_br_if.match(ifDescr):        
            return "net-bridge_"+cleanName(re_br_if.match(ifDescr).group(1))
        if re_tap_if.match(ifDescr):        
            return "net-Tap_"+cleanName(re_tap_if.match(ifDescr).group(1))
        if re_foo_numbered.match(ifDescr):        
            return "net-"+cleanName(re_foo_numbered.match(ifDescr).group(1))+'_'+cleanName(re_foo_numbered.match(ifDescr).group(2))
        return ifDescr
    
    try:
        m.ifHCInOctets[1]
    except Exception:
        inOctetHC = 0
    else:
        inOctetHC = 1
    print "Input values are on "+str(32*(1+inOctetHC))+"b"
    maxValIn = 2**(32*(1+inOctetHC))
    
    try:
        m.ifHCOutOctets[1]
    except Exception:
        outOctetHC = 0
    else:
        outOctetHC = 1
    print "Output values are on "+str(32*(1+outOctetHC))+"b"
    maxValOut = 2**(32*(1+outOctetHC))

    print "List of all interfaces:"
    for idx in m.ifName:
        if m.ifDescr[idx] == "lo":
            continue
        print " * " +m.ifDescr[idx]+ " - ID: "+str(idx)
        ifDescr = getShortIfName(m.ifDescr[idx])
        ifInOctets = long(m.ifHCInOctets[idx]) if inOctetHC else long(m.ifInOctets[idx])
        ifOutOctets = long(m.ifHCOutOctets[idx]) if outOctetHC else long(m.ifOutOctets[idx])
        oldifVal[ifDescr] = [ifInOctets, ifOutOctets]
    if len(list_only_net_idx) > 0:
        print "Actual filter limite interfaces to "+str(list_only_net_idx)
    else:
        print "No filter on interface list is set"

def get_send_net_interface(m, idx):
    if m.ifDescr[idx] == "lo":
        return 0
    ifDescr = getShortIfName(m.ifDescr[idx])
    ifInOctets = long(m.ifHCInOctets[idx]) if inOctetHC else long(m.ifInOctets[idx])
    ifOutOctets = long(m.ifHCOutOctets[idx]) if outOctetHC else long(m.ifOutOctets[idx])
    delta_ifInOctets =  (ifInOctets - oldifVal[ifDescr][0])/2**20
    if delta_ifInOctets < 0:
        delta_ifInOctets =  (maxValIn - oldifVal[ifDescr][0] + ifInOctets)/2**20
        print "Negatif IN : {} => {} - {} = {}, I send {}".format(hostname+"_"+ifDescr+'-Mbytes-In',ifInOctets,oldifVal[ifDescr][0],(ifInOctets - oldifVal[ifDescr][0])/2**20,delta_ifInOctets)
    delta_ifOutOctets = (ifOutOctets - oldifVal[ifDescr][1])/2**20
    if delta_ifOutOctets < 0:
        delta_ifInOctets =  (maxValOut - oldifVal[ifDescr][1] + ifOutOctets)/2**20
        print "Negatif Out : {} => {} - {} = {}, I send {}".format(hostname+"_"+ifDescr+'-Mbytes-Out',ifOutOctets,oldifVal[ifDescr][1],(ifOutOctets - oldifVal[ifDescr][1])/2**20,delta_ifOutOctets)
    oldifVal[ifDescr] = [ifInOctets,ifOutOctets]
    redPush( hostname+"_"+ifDescr+'-Mbytes-Out',t+"/"+str(delta_ifOutOctets))
    redPush( hostname+"_"+ifDescr+'-Mbytes-In',t+"/"+str(delta_ifInOctets))


def get_send_net():
    if send_net:
        idx_list = list_only_net_idx if len(list_only_net_idx) > 0 else m.ifName
        for idx in idx_list:
            get_send_net_interface(m,idx)
            
# Catch CTRL+C
def signal_handler(signal, frame):
        print("\nUnregister to nodes_list")
        r.srem('nodes_list',hostname)
        sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)
print('\nPress Ctrl+C to exit')

##
# Sending loop
##
next_call = time.time()
while (1):
    next_call += sending_interval
    t = str(int(time.time()*1000))
    get_send_net()
    print "Wait..."
    while(time.time()<next_call):
        time.sleep(0.1)
