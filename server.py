#!/usr/bin/env python3

import socket
import socketserver
import sys
import threading
import re



zoneFile = open("./trackers/zones", "r+")


def getLocation(device):
    pass


def setZone(device, zone):
    pass


def setLocation(device, location):
    pass


def getZone(device):
    pass


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = str(self.request.recv(1024), 'ascii')
        print("Server recieved: '{}' from {}".format(data, self.client_address[0]))
        response = bytes()

        # if data is asking for the location of a device, send that back
        """ to ask for the location of BB_0, data would be 'getLocation BB_0'
            Basically a string that looks like a function """
        if "getLocation" in data:
            device = data.split(' ')[1] # gets the portion of the string after first whitespace
            response = bytes(getLocation(device), 'ascii')
        
        # if data is sending a zone for a device, add that data to its file
        """ to set the allowed zone of a device, data would look like 'setZone BB_0 (xx.xxN,xx.xxW),xx.xx' """
        elif "setZone" in data:
            device, zone = data.split(' ')[1:2]
            setZone(device, zone)
        
        # if data is a device sending it's location, append that to its file
        """ to send the location of a device, data would look like 'setLocation BB_0 xx.xxN,xx.xxW' """
        elif "setLocation" in data:
            device, location = data.split(' ')[1:2]
            setLocation(device, location)

        # if data is a device asikng where it's allowed to be, read its file to see if it has been assigned a zone
            # if it has a zone, return that. Otherwise, return ""
        """ to recieve the zone set for a device, data would look like 'getZone BB_0' """
        elif "getZone" in data:
            device = data.split(' ')[1]
            response = bytes(getZone(device), 'ascii')

        if response:
            print("Server sent: {}".format(response))
            self.request.sendall(response)

    def finish(self):
        self.handle()


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


def client(ip, port, message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip, port))
        sock.sendall(bytes(message, 'ascii'))
        response = str(sock.recv(1024), 'ascii')
        print("Client Received: {}".format(response))


if __name__ == "__main__":
    # Port 0 means to select an arbitrary unused port
    HOST, PORT = '', 6969

    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    with server:
        ip, port = server.server_address

        # Start a thread with the server -- that thread will then start one
        # more thread for each request
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()
        print("Server loop running in thread:", server_thread.name)

#        client(ip, port, "Hello World 1")
#        client(ip, port, "Hello World 2")
#        client(ip, port, "Hello World 3")

        shutdown = input("Press Enter to shutdown server: \n")
        server.shutdown()
