#!/usr/bin/python

import psutil
import redis 
import socket
import time
import sys
import signal


sending_interval = 1 #in second
history = 60
send_cpu = 1
send_mem = 1
send_net = 1

##
# Prepare hostname
##
hostname = socket.gethostname()
t = str(int(time.time()*1000))

##
# Check argument and connect to REDIS
##
if len(sys.argv)==2:
    rtns_ip = sys.argv[1]
    rtns_password = ""
elif len(sys.argv)==3:
	rtns_ip = sys.argv[1]
	rtns_password = sys.argv[2]
else:
	print "Usage: ./rtns-agent-redis.py RTNS_SERVER_IP [PASSWORD]\n"
	raise SystemExit
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

# Send CPU data
if send_cpu:
    cpu_i = 0
    for cpu in psutil.cpu_percent(percpu=True):
        print hostname+"_cpu_"+str(cpu_i)
        cpu_i += 1

def get_send_cpu_or_sleep():
    if send_cpu:
        cpu_i = 0
        for cpu in psutil.cpu_percent(interval=sending_interval,percpu=True):
            redPush( hostname+"_cpu_"+str(cpu_i),t+"/"+str(cpu))
            cpu_i += 1
    else:
        time.sleep(sending_interval)

# Send Mem data
if send_mem:
    print hostname+"_mem_used"

def get_send_mem():
    if send_mem:
        redPush( hostname+"_mem_used",t+"/"+str(psutil.virtual_memory().percent))

# Send Net data
if send_net:
    nic_old= {}
    net_stats = psutil.net_io_counters(pernic=True)
    for nic in net_stats.keys():
        print hostname+"_nic_"+str(nic)+'-bytes-send'
        print hostname+"_nic_"+str(nic)+'-bytes-recv'
        nic_old[nic+"_sent"]=net_stats[nic].bytes_sent
        nic_old[nic+"_recv"]=net_stats[nic].bytes_recv

def get_send_net():
    if send_net:    
        net_stats = psutil.net_io_counters(pernic=True)
        for nic in net_stats.keys():
            redPush( hostname+"_nic_"+str(nic)+'-bytes-send',t+"/"+str(net_stats[nic].bytes_sent-nic_old[nic+"_sent"]))
            redPush( hostname+"_nic_"+str(nic)+'-bytes-recv',t+"/"+str(net_stats[nic].bytes_recv-nic_old[nic+"_recv"]))
            nic_old[nic+"_sent"]=net_stats[nic].bytes_sent
            nic_old[nic+"_recv"]=net_stats[nic].bytes_recv

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
    
while (1):
    #~ cpu_percent with interval give the tempo (1sec))
    t = str(int(time.time()*1000))
    get_send_cpu_or_sleep()
    get_send_mem()
    get_send_net()

