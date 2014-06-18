#!/usr/bin/python

import psutil
import redis 
import socket
import time
import sys

hostname = socket.gethostname()+"_"
history = 60;

if len(sys.argv)==2:
	rtns_ip = sys.argv[1]
else:
	print "Usage: ./rtns-agent-redis.py RTNS_SERVER_IP\n"
	raise SystemExit

r = redis.Redis(rtns_ip)

r.sadd('nodes_list',hostname)

def redPush( key, val):
    r.lpush(key,val)
    r.ltrim(key, 0, history)

nic_old= {}
net_stats = psutil.net_io_counters(pernic=True)
for nic in net_stats.keys():
    nic_old[nic+"_sent"]=net_stats[nic].bytes_sent
    nic_old[nic+"_recv"]=net_stats[nic].bytes_recv

while (1):
    #~ cpu_percent with interval give the tempo (1sec))
    t = str(int(time.time()*1000))
    cpu_i = 0
    for cpu in psutil.cpu_percent(interval=1,percpu=True):
        redPush( hostname+"cpu_"+str(cpu_i),t+"/"+str(cpu))
        cpu_i += 1
    net_stats = psutil.net_io_counters(pernic=True)
    for nic in net_stats.keys():
        redPush( hostname+"nic_"+str(nic)+'-bytes-send',t+"/"+str(net_stats[nic].bytes_sent-nic_old[nic+"_sent"]))
        redPush( hostname+"nic_"+str(nic)+'-bytes-recv',t+"/"+str(net_stats[nic].bytes_recv-nic_old[nic+"_recv"]))
        nic_old[nic+"_sent"]=net_stats[nic].bytes_sent
        nic_old[nic+"_recv"]=net_stats[nic].bytes_recv
    redPush( hostname+"mem_used",t+"/"+str(psutil.virtual_memory().percent))

