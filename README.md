Real-Time-Nodes-Statistics
==========================

Real Time Nodes Statistics, aka RTNS, is a software providing real time statistics of remote nodes.

The web client shows CPU/Mem/Net/... statistics, node by node. Compared to other tools, the client is not fetching data on a server, it subscribe to data evolution, and receive new statistic values when they are available. If the supervised node publish a new value each second, the client will get them immediatly, second after second.

The software is based on:
* an python agent publishing statistics from the supervised nodes
* a redis server
* a python web server, compatible with websocket
* a JS web client
