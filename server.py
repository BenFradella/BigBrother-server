#!/usr/bin/env python3

import socket
import socketserver

import threading
from time import sleep

import os
import json
import struct

from sys import platform


with open('knownClients.json') as clientFile:
    knownClients = json.load(clientFile)
# note -- the files are full of garbage data right now
# just for testing purposes
fileDir = "./trackers/"
zoneFile = fileDir + "zones"
zoneMutex = threading.Lock()

locationFiles = {}
for root, dirs, files in os.walk(fileDir):
    for file in files:
        if "BB_" in file:
            locationFiles[file] = fileDir + file
locationMutex = {}
for file in locationFiles:
    locationMutex[file] = threading.Lock()


def getLocation(device):
    response = ""

    try:
        with open(locationFiles[device], "r+") as lf:
            for line in lf:
                response += line
    except KeyError:
        response += "0.0N,0.0W"

    return response


def setZone(device, zone):
    zoneMutex.acquire()
    newDevice = True

    with open(zoneFile, "r+") as zf:
        for num, line in enumerate(zf, 0):
            if device in line:
                zf.seek(0)
                lines = zf.readlines()
                zf.seek(0)
                lines[num] = device + ' ' + zone + '\n'
                zf.truncate()
                zf.writelines(lines)
                zoneMutex.release()
                newDevice = False
                break
        if newDevice:
            zf.write(device + ' ' + zone + '\n')
            zoneMutex.release()


def setLocation(device, location):
    try:
        locationMutex[device].acquire()
    except KeyError:
        locationFiles[device] = fileDir + device
        locationMutex[device] = threading.Lock()
        locationMutex[device].acquire()

    with open(locationFiles[device], "a+") as lf:
        lf.write(location + '\n')

    locationMutex[device].release()


def getZone(device):
    response = ""

    with open(zoneFile, "r+") as zf:
        for line in zf:
            if device in line:
                response += line.split(' ')[1]
                break
    if response == "":
        response += "0.0N,0.0W,0.0"

    return response


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = ""
        clientIp = self.client_address[0]

        while data != "Goodbye":
            data = self.readUTF()
            if clientIp not in knownClients:
                if "observer" in data:
                    knownClients[clientIp] = "android"
                else:
                    knownClients[clientIp] = "bigBrother"
            print("\nServer recieved: '{}' from {}".format(data, clientIp))
            response = ""

            if "getLocation" in data:
                device = data.split(' ')[1]
                response = getLocation(device)
            elif "setZone" in data:
                device, zone = data.split(' ')[1:3]
                setZone(device, zone)
            elif "setLocation" in data:
                device, location = data.split(' ')[1:3]
                setLocation(device, location)
            elif "getZone" in data:
                device = data.split(' ')[1]
                response = getZone(device)
            
            if response != "":
                print("Server sent: {}".format(response))
                self.writeUTF(response)
            
            sleep(0.02)  # max 50 hertz tickrate to save cpu resources

    def finish(self):
        print("connection with {} closed".format(self.client_address[0]))
        self.request.close()

    def readUTF(self):
        # get number of bytes to receive
        utf_length = struct.unpack('>H', self.request.recv(2))[0]
        return str(self.request.recv(utf_length), "utf-8")

    def writeUTF(self, message):
        utf_length = struct.pack(">H", len(message))
        self.request.send(utf_length)  # send length of string
        self.request.send(message.encode("utf-8"))  # send string


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


def client(ip, port, message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        def writeUTF(msg):
            sock.send(struct.pack(">H", len(msg)))
            sock.send(msg.encode("utf-8"))

        sock.connect((ip, port))
        writeUTF("Hello from an observer")
        writeUTF(message)
        if "get" in message:
            utf_length = struct.unpack('>H', sock.recv(2))[0]
            response = str(sock.recv(utf_length), "utf-8")
            print("\nClient Received: {}".format(response))
        writeUTF("Goodbye")


if __name__ == "__main__":
    if "win" in platform:
        # assign the server ip to your machine's local ip address.
        # I don't know whether any windows machines will be able to accept
        # connections from outside their local network or not but the local
        # client objects will still work for testing commands
        IP = socket.gethostbyname(socket.gethostname())
    else:
        IP = ''

    # Port 0 means to select an arbitrary unused port
    HOST, PORT = IP, 6969

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

        # test server functions with client objects here
        # client(ip, port, "getLocation BB_0")
        # client(ip, port, "getZone BB_3")
        # client(ip, port, "setLocation BB_2 0.0N,0.0W,0.0")

        shutdown = input("Press Enter to shutdown server: \n")
        server.shutdown()

    with open('knownClients.json', 'w') as clientFile:
        json.dump(knownClients, clientFile, indent=4)
