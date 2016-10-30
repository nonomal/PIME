#! python3
# Copyright (C) 2015 - 2016 Hong Jen Yee (PCMan) <pcman.tw@gmail.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import json
import sys
import os
import random
import uuid
import time

import tornado.ioloop
import tornado.web

from serviceManager import textServiceMgr


server = None


class Client(object):
    def __init__(self, server):
        self.server = server
        self.service = None

    def init(self, msg):
        self.guid = msg["id"]
        self.isWindows8Above = msg["isWindows8Above"]
        self.isMetroApp = msg["isMetroApp"]
        self.isUiLess = msg["isUiLess"]
        self.isUiLess = msg["isConsole"]
        # create the text service
        self.service = textServiceMgr.createService(self, self.guid)
        return (self.service is not None)

    def handleRequest(self, msg): # msg is a json object
        method = msg.get("method", None)
        seqNum = msg.get("seqNum", 0)
        # print("handle message: ", str(id(self)), method, seqNum)
        service = self.service
        if service:
            # let the text service handle the message
            reply = service.handleRequest(msg)
        else:  # the text service is not yet initialized
            reply = {"seqNum": seqNum}
            success = False
            if method == "init": # initialize the text service
                success = self.init(msg)
            reply["success"] = success
        # print(reply)
        return reply

        
class MainHandler(tornado.web.RequestHandler):

    def get(self, args):  # ping the API endpoint
        self.write("pong")

    def post(self, client_id=None):
        global server
        if not client_id:  # add new client
            client_id = server.new_client()
            self.write(client_id)
        else:  # existing client
            client = server.clients.get(client_id, None)
            if client:
                msg = json.loads(self.request.body.decode("UTF-8"))
                # print("received msg", success, msg)
                reply = client.handleRequest(msg)
                replyText = json.dumps(reply) # convert object to json
                self.write(replyText)
            else:
                self.write("")

    def delete(self, client_id=None):
     if client_id:
         server.remove_client(client_id)


class Server(object):
    def __init__(self):
        self.clients = {}
        # FIXME: this uses the AppData/Roaming dir, but we want the local one.
        #        alternatively, use the AppData/Temp dir.
        self.config_dir = os.path.join(os.path.expandvars("%APPDATA%"), "PIME", "run")
        self.info_file = os.path.join(self.config_dir, "python.json")
        os.makedirs(self.config_dir, mode=0o700, exist_ok=True)

    def __del__(self):
        if self.info_file:
            os.unlink(self.info_file)
        
    def run(self):
        app = tornado.web.Application([
            (r"/(.*)", MainHandler),
        ])
        # find an available port
        while True:
            port = random.randint(1025, 65535)
            try:
                app.listen(port, "127.0.0.1")
                break
            except OSError:  # port is in use, try another one
                continue

        # write the server info to file
        with open(self.info_file, "w") as f:
            info = {
                "pid": os.getpid(),  # process ID
                "port": port,  # the http port
                "access_token": str(uuid.uuid4()),  # access token to this server
                "timestamp": int(time.time())
            }
            json.dump(info, f, indent=2)

        # setup the main event loop
        loop = tornado.ioloop.IOLoop.current()
        loop.start()

    def new_client(self):
        # create a Client instance for the client
        client = Client(self)
        client_id = str(id(client))
        self.clients[client_id] = client
        print("new client:", client_id)
        return client_id

    def remove_client(self, client_id):
        print("client disconnected:", client_id)
        del self.clients[client_id]


def main():
    global server
    server = Server()
    server.run()


if __name__ == "__main__":
    main()
