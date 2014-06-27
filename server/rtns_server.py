#!/usr/bin/python
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
#~ Module name: Real Time Node Supervision - Server
#~ Version:     1.0
#~ Created:     2014-06-27 by David Blaisonneau
#~ 

from __future__ import print_function
import tornado.httpserver
import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.gen
import json
import tornadoredis
import redis
import socket
import os
import logging
import logging.handlers
import sys

#~ if available, get the redis password
redis_password = sys.argv[1] if len(sys.argv)==2 else ""

    
#~ Connect to Redis
c = tornadoredis.Client()
c.connect()

hostname=socket.getfqdn()
my_logger = logging.getLogger('MyLogger')
my_logger.setLevel(logging.INFO)
handler = logging.handlers.SysLogHandler(address = '/dev/log')
my_logger.addHandler(handler)

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        url = "wss://%s/ws" % self.request.host
        my_logger.info("New connection from: "+self.request.remote_ip)
        self.render("template.html", ws_server_url=url)
           
class MessageHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super(MessageHandler, self).__init__(*args, **kwargs)
        if self.request.headers.get('Upgrade')=='websocket':
            my_logger.info("New WS connection from: "+self.request.remote_ip)
            self.listen()
        else:
            my_logger.error("Bad WS connection from: "+self.request.remote_ip)
    
    @tornado.gen.engine
    def listen(self):
        my_logger.error("Server: Connect to redis")
        #~ self.client_classic = redis.Redis({'password':redis_password})
        self.client_classic = redis.Redis()
        self.client_classic.config_set('notify-keyspace-events','KA')
        self.client_pubsub = tornadoredis.Client()
        self.client_pubsub.connect()
        #~ yield tornado.gen.Task(self.client_pubsub.auth, redis_password)
        yield tornado.gen.Task(self.client_pubsub.psubscribe, '__key*__:nodes_list')
        self.client_pubsub.listen(self.on_message)
        self.nodes_list = self.client_classic.smembers('nodes_list')
        self.send_nodes_list(self.nodes_list)

    @tornado.gen.engine
    def on_message(self, msg):
        #~ Message from Redis
        if hasattr(msg,'kind'):
            #~ Publish message
            if msg.kind == 'pmessage':
                if(msg.body == 'lpush'):
                    key = msg.channel.split(':')[1]
                    self.write_message('{"' + key + '":"' + str(self.client_classic.lrange(key,0,0)[0]) +'"}')
                    my_logger.debug("Redis:: psh: "+key)
                if(msg.body == 'sadd'):
                    old_list = self.nodes_list
                    self.nodes_list = self.client_classic.smembers('nodes_list')
                    self.send_add_nodes(list(self.nodes_list-old_list)[0])
                    my_logger.info("Redis:: new node: "+str(list(self.nodes_list-old_list)))
                if (msg.body == 'srem'):
                    old_list = self.nodes_list
                    self.nodes_list = self.client_classic.smembers('nodes_list')
                    self.send_rem_nodes(list(old_list-self.nodes_list)[0])
                    my_logger.info("Redis:: node removed: "+str(list(old_list-self.nodes_list)))
            #~ Subscription confirmation
            elif msg.kind == 'psubscribe':
                self.send_message("New subscription on key: " + msg.channel.split(':')[1])
            #~ UnSubscription confirmation
            elif msg.kind == 'punsubscribe':
                self.send_message("Unsubscription of key: " + msg.channel.split(':')[1])
            #~ Disconnected from redis
            elif msg.kind == 'disconnect':
                self.send_message( "The connection terminated due to a Redis server error.")
                my_logger.error("Redis disconnected")
                self.close()
            else:
                self.write_message(str(msg))
        #~ Message from the client throug WebSocket
        else:
            wsdata = json.loads(msg)
            #~ Client subscribe a new key
            if wsdata.has_key('listStats'):
                node = wsdata['listStats']
                my_logger.info("Client:: "+self.request.remote_ip+" require list of stats for "+str(node))
                self.send_list_stats(node,self.client_classic.keys(node+'*'))                
            #~ Client subscribe a new key
            elif wsdata.has_key('subscribe'):
                my_logger.info("Client:: "+self.request.remote_ip+" subscribe to "+wsdata['subscribe'])
                yield tornado.gen.Task(self.client_pubsub.psubscribe, '__key*__:'+wsdata['subscribe'])
            #~ Client unsubscribe a key
            elif wsdata.has_key('unsubscribe'):
                my_logger.info("Client:: "+self.request.remote_ip+" unsubscribe to "+wsdata['unsubscribe'])
                self.client_pubsub.punsubscribe('__key*__:'+wsdata['unsubscribe'])
        
    def send_message(self, msg):
        self.send_value("_msg",msg)
                
    def send_list_stats(self, node, listStats):
        if type(node) == list:
            node = node[0]
        my_logger.info("Server:: send_list_stats: "+str(listStats))
        self.write_message('{ "_nodes_stats" : { "'+node+'" : ' + json.dumps(list(listStats)) + '}}')
        
    def send_add_nodes(self, node):
        self.write_message('{ "_node_add" : ' + json.dumps(node) + '}')
        
    def send_rem_nodes(self, node):
        self.write_message('{ "_node_rem" : ' + json.dumps(node) + '}')
        
    def send_nodes_list(self, n_list):
        self.write_message('{ "_nodes_list" : ' + json.dumps(list(n_list)) + '}')
        
    def send_value(self, key, value):
        self.write_message('{ "'+key+'" : "' + value + '"}')
        
    def on_close(self):
        if self.client_pubsub.subscribed:
            self.client_pubsub.punsubscribe('__key*__:*')
            self.client_pubsub.disconnect()


application = tornado.web.Application([
    (r'/', MainHandler),
    (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': r"./static/"},),
    (r'/ws', MessageHandler),
])

if __name__ == '__main__':
    http_server = tornado.httpserver.HTTPServer(application, ssl_options={
		"certfile": "server.crt",
		"keyfile":  "server.key",
	})
    http_server.listen(8888)
    print('Server is runing at 0.0.0.0:8888\nQuit the server with CONTROL-C')
    tornado.ioloop.IOLoop.instance().start()
