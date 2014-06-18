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

c = tornadoredis.Client()
c.connect()

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        url = "ws://%s:8888/ws" % "127.0.0.1"
        self.render("template.html", ws_server_url=url)
        
class JSHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("canvasjs.min.js")

class MessageHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super(MessageHandler, self).__init__(*args, **kwargs)
        self.listen()

    @tornado.gen.engine
    def listen(self):
        self.client_pubsub = tornadoredis.Client()
        self.client_read = redis.Redis()
        self.client_pubsub.connect()
        self.client_pubsub.execute_command('CONFIG SET','notify-keyspace-events','KA',callback=None)
        yield tornado.gen.Task(self.client_pubsub.psubscribe, '__key*__:nodes_list')
        self.client_pubsub.listen(self.on_message)

    @tornado.gen.engine
    def on_message(self, msg):
        #~ Message from Redis
        if hasattr(msg,'kind'):
            #~ Publish message
            if msg.kind == 'pmessage':
                if(msg.body == 'lpush'):
                    key = msg.channel.split(':')[1]
                    self.write_message('{"' + key + '":"' + str(self.client_read.lrange(key,0,0)[0]) +'"}')
                if(msg.body == 'sadd' or msg.body == 'srem'):
                     self.send_message("nodes list update") 
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
            if wsdata.has_key('subscribe'):
                yield tornado.gen.Task(self.client_pubsub.psubscribe, '__key*__:'+wsdata['subscribe'])
            #~ Client unsubscribe a key
            elif wsdata.has_key('unsubscribe'):
                self.client_pubsub.punsubscribe('__key*__:'+wsdata['unsubscribe'])
        
    def send_message(self, msg):
        self.send_value("_msg",msg)
        
    def send_value(self, key, value):
        self.write_message('{ "'+key+'" : "' + value + '"}')
        
    def on_close(self):
        if self.client_pubsub.subscribed:
            self.client_pubsub.punsubscribe('__key*__:*')
            self.client_pubsub.disconnect()


application = tornado.web.Application([
    (r'/', MainHandler),
    (r'/js/canvasjs.min.js', JSHandler),
    (r'/ws', MessageHandler),
])

if __name__ == '__main__':
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    print('Server is runing at 0.0.0.0:8888\nQuit the server with CONTROL-C')
    tornado.ioloop.IOLoop.instance().start()
