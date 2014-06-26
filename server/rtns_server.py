#!/usr/bin/python

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

c = tornadoredis.Client()
c.connect()
hostname=socket.getfqdn()

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        url = "ws://%s/ws" % self.request.host
        #~ url = "ws://%s/ws" % "127.0.0.1:8888"
        #~ url = "ws://%s/ws" % "10.193.5.79"
        self.render("template.html", ws_server_url=url)
           
class MessageHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super(MessageHandler, self).__init__(*args, **kwargs)
        #~ print self.request
        self.listen()
    
    @tornado.gen.engine
    def listen(self):
        self.client_pubsub = tornadoredis.Client()
        self.client_classic = redis.Redis()
        self.client_classic.config_set('notify-keyspace-events','KA')
        self.client_pubsub.connect()
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
                if(msg.body == 'sadd'):
                    old_list = self.nodes_list
                    self.nodes_list = self.client_classic.smembers('nodes_list')
                    self.send_add_nodes(list(self.nodes_list-old_list))
                if (msg.body == 'srem'):
                    old_list = self.nodes_list
                    self.nodes_list = self.client_classic.smembers('nodes_list')
                    self.send_rem_nodes(list(old_list-self.nodes_list))
            #~ Subscription confirmation
            elif msg.kind == 'psubscribe':
                self.send_message("New subscription on key: " + msg.channel.split(':')[1])
            #~ UnSubscription confirmation
            elif msg.kind == 'punsubscribe':
                self.send_message("Unsubscription of key: " + msg.channel.split(':')[1])
            #~ Disconnected from redis
            elif msg.kind == 'disconnect':
                self.send_message( "The connection terminated due to a Redis server error.")
                self.close()
            else:
                self.write_message(str(msg))
        #~ Message from the client throug WebSocket
        else:
            wsdata = json.loads(msg)
            #~ Client subscribe a new key
            if wsdata.has_key('listStats'):
                node = wsdata['listStats']
                self.send_list_stats(node,self.client_classic.keys(node+'*'))                
            #~ Client subscribe a new key
            elif wsdata.has_key('subscribe'):
                yield tornado.gen.Task(self.client_pubsub.psubscribe, '__key*__:'+wsdata['subscribe'])
            #~ Client unsubscribe a key
            elif wsdata.has_key('unsubscribe'):
                self.client_pubsub.punsubscribe('__key*__:'+wsdata['unsubscribe'])
        
    def send_message(self, msg):
        self.send_value("_msg",msg)
                
    def send_list_stats(self, node, listStats):
        self.write_message('{ "_nodes_stats" : { "'+node+'" : ' + json.dumps(list(listStats)) + '}}')
        
    def send_add_nodes(self, node):
        self.write_message('{ "_nodes_add" : ' + json.dumps(list(node)) + '}')
        
    def send_rem_nodes(self, node):
        self.write_message('{ "_nodes_rem" : ' + json.dumps(list(node)) + '}')
        
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
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    print('Server is runing at 0.0.0.0:8888\nQuit the server with CONTROL-C')
    tornado.ioloop.IOLoop.instance().start()
