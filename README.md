Real-Time-Nodes-Statistics
==========================

Real Time Nodes Statistics, aka RTNS, is a software providing real time statistics of remote nodes.

The web client shows CPU/Mem/Net/... statistics, node by node. Compared to other tools, the server is not fetching data on a server, the client subscribe to data evolution, and receive new statistic values when they are available. If the supervised node publish a new value each second, the client will get them immediatly, second after second.

The software is based on:
* an python agent publishing statistics from the supervised nodes
* a redis server
* a python web server, compatible with websocket
* a JS web client

Agents
------------

* Dependencies

The RTNS agent needs two libraries. Redis > 2.8 and PSUtils >= 1.2.1

On Debian like sytems installation, installation steps are:
```
wget https://pypi.python.org/packages/source/r/redis/redis-2.10.1.tar.gz
tar zxf redis-2.10.1.tar.gz
cd redis-2.10.1
sudo python setup.py install
cd
sudo apt-get install python-psutil
```

* Running the agent

./rtns-agent-redis.py IPADDRESS_OF_RTNS_SERVER
