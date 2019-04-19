#!/usr/bin/env python3

import socket
import socketserver

import threading
from time import sleep

import os
import json
import struct

from sys import platform


fileDir = "./data/"

# load/create knownClients file
try:
    with open(fileDir + 'knownClients.json') as clientFile:
        knownClients = json.load(clientFile)
except FileNotFoundError:
    with open(fileDir + 'knownClients.json', 'w+') as clientFile:
        knownClients = {}
        knownClients['127.0.0.1'] = {'type': 'android'}
        json.dump(knownClients, clientFile, indent=4)

# put all device files in a dict, create dict of associated mutex locks
deviceFiles = {}
for _, _, files in os.walk(fileDir):
    for file in files:
        if "BB_" in file:
            deviceFiles[file.split('.')[0]] = fileDir + file
deviceMutex = {}
for device in deviceFiles:
    deviceMutex[device] = threading.Lock()


def addDeviceIfNew(device):
    if device not in deviceFiles:
        fileName = fileDir + device + '.json'
        with open(fileName, 'w+') as df:
            init = {}
            init['location'] = []
            init['zone'] = []
            json.dump(init, df, indent=4)
        deviceFiles[device] = fileName
        deviceMutex[device] = threading.Lock()


def getLocation(device):
    addDeviceIfNew(device)
    response = ""

    with open(deviceFiles[device], "r+") as df:
        data = json.load(df)
        try:
            response = data['location'][-1]
        except IndexError:
            response = "0.0N,0.0W"

    return response


def setZone(device, zone):
    addDeviceIfNew(device)
    deviceMutex[device].acquire()

    with open(deviceFiles[device], "r+") as df:
        data = json.load(df)
        data['zone'] = zone.split('\n')
        df.seek(0)
        json.dump(data, df, indent=4)

    deviceMutex[device].release()


def setLocation(device, location):
    addDeviceIfNew(device)
    deviceMutex[device].acquire()

    with open(deviceFiles[device], "r+") as df:
        data = json.load(df)
        data['location'].append(location)
        df.seek(0)
        json.dump(data, df, indent=4)

    deviceMutex[device].release()


def getZone(device):
    addDeviceIfNew(device)
    response = ""

    with open(deviceFiles[device], "r+") as df:
        data = json.load(df)
        if len(data['zone']) > 0:
            response = '\n'.join(data['zone'])
        else:
            response = "0.0N,0.0W,0.0"

    return response


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = ""
        clientIp = self.client_address[0]

        while data != "Goodbye":
            data = self.readUTF()

            if clientIp not in knownClients:
                knownClients[clientIp] = {}
                if "observer" in data:
                    knownClients[clientIp]['type'] = "android"
                else:
                    knownClients[clientIp]['type'] = "bigBrother"

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
        bytes_length = self.request.recv(2)
        if len(bytes_length) >= 2:
            utf_length = struct.unpack('!H', bytes_length)[0]
            return str(self.request.recv(utf_length), "utf-8")
        else:
            return ''

    def writeUTF(self, message):
        utf_length = struct.pack("!H", len(message))
        self.request.send(utf_length)  # send length of string
        self.request.send(message.encode("utf-8"))  # send string


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


def client(ip, port, message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        def writeUTF(msg):
            sock.send(struct.pack("!H", len(msg)))
            sock.send(msg.encode("utf-8"))

        sock.connect((ip, port))
        writeUTF("Hello from an observer")
        writeUTF(message)
        if "get" in message:
            utf_length = struct.unpack('!H', sock.recv(2))[0]
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

        """test server functions with client objects here"""
        # client(ip, port, "setLocation BB_2 0.324N,40.432E")
        # client(ip, port, "getLocation BB_2")
        # client(ip, port, "setZone BB_2 0.324N,40.432E,4.13")
        # client(ip, port, "getZone BB_2")

        shutdown = input("Press Enter to shutdown server: \n")
        server.shutdown()

    with open(fileDir + 'knownClients.json', 'w') as clientFile:
        json.dump(knownClients, clientFile, indent=4)
