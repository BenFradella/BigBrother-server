#!/usr/bin/env python3

import socket
import socketserver
import sys
from sys import platform
import os
import threading
import re


# note -- the files are full of garbage data right now, just for testing purposes
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
    except:
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
    except:
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
        data = str(self.request.recv(1024), 'ascii')
        print("\nServer recieved: '{}' from {}".format(data, self.client_address[0]))
        response = bytes()

        # if data is asking for the location of a device, send that back
        # to ask for the location of BB_0, data would be 'getLocation BB_0'
        # Basically a string that looks like a function
        if "getLocation" in data:
            device = data.split(' ')[1] # gets the portion of the string after first whitespace
            response = bytes(getLocation(device), 'ascii')
        
        # if data is sending a zone for a device, add that data to its file
        # to set the allowed zone of a device, data would look like 'setZone BB_0 xx.xxN,xx.xxW,xx.xx'
        elif "setZone" in data:
            device, zone = data.split(' ')[1:3]
            setZone(device, zone)
        
        # if data is a device sending it's location, append that to its file
        # to send the location of a device, data would look like 'setLocation BB_0 xx.xxN,xx.xxW'
        elif "setLocation" in data:
            device, location = data.split(' ')[1:3]
            setLocation(device, location)

        # if data is a device asikng where it's allowed to be, read its file to see if it has been assigned a zone
            # if it has a zone, return that. Otherwise, return ""
        # to recieve the zone set for a device, data would look like 'getZone BB_0'
        elif "getZone" in data:
            device = data.split(' ')[1]
            response = bytes(getZone(device), 'ascii')

        if response:
            numBytes = len(response).to_bytes(2, 'big')
            response = numBytes + response
            print("Server sent: {}".format(response))
            self.request.sendall(response)

    def finish(self):
        # setup to handle another request instead of closing the connection
        self.handle()


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


def client(ip, port, message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip, port))
        sock.sendall(bytes(message, 'ascii'))
        if "get" in message:
            response = str(sock.recv(1024), 'ascii')
            print("\nClient Received: {}".format(response))


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
        client(ip, port, "getLocation BB_0")
        client(ip, port, "getZone BB_3")
        client(ip, port, "setLocation BB_2 0.0N,0.0W,0.0")

        shutdown = input("Press Enter to shutdown server: \n")
        server.shutdown()
