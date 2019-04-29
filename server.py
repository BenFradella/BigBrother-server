#!/usr/bin/env python3

import socket
import socketserver

import threading
from time import sleep
from select import select
import re

import pathlib
import os
import json
import struct

from colorama import Fore, Style, init, deinit
from sys import platform


init()  # initialize stdin and stderr for colors

timeout = 10.0  # how long until connection is closed after not receiving any data
tickrate = 50.00

fileDir = "./data/"
pathlib.Path(fileDir).mkdir(parents=True, exist_ok=True)


# load/create knownClients
try:
    with open(fileDir + 'knownClients.json') as clientFile:
        knownClients = json.load(clientFile)
except FileNotFoundError:
    knownClients = {}

# put all device files in a dict, create dict of associated mutex locks
deviceFiles = {}
for _, _, files in os.walk(fileDir):
    for file in files:
        if "BB_" in file:
            deviceFiles[os.path.splitext(file)[0]] = fileDir + file
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
            response = "0.0N,0.0E"

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
            response = "0.0N,0.0E,0.0"

    return response


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.setblocking(0)

        data = ""
        clientIp = self.client_address[0]

        reDict = {
            'getLocation': r"^getLocation (?P<device>BB_\d+)$",
            'setLocation': r"^setLocation (?P<device>BB_\d+) (?P<location>\d+(.\d+)?[NS],\d+(.\d+)?[EW])$",
            'getZone': r"^getZone (?P<device>BB_\d+)$",
            'setZone': r"^setZone (?P<device>BB_\d+) (?P<zone>((\d+(.\d+)?[NS],\d+(.\d+)?[EW]),\d+(.\d+)?(\n)?)+)$"
        }

        while True:
            sleep(0.02)  # max 50 hertz tickrate to save cpu resources
            data = self.readUTF()

            if (data is not None) and (data != "Goodbye"):
                if clientIp not in knownClients:
                    if "setZone" in data:
                        knownClients[clientIp] = {'type': "android"}
                        knownClients[clientIp]['lastLocationSent'] = {}
                    elif "setLocation" in data:
                        knownClients[clientIp] = {'type': "bigBrother"}

                self.clientPrint("{} sent: '{}'".format(clientIp, data))
                response = ""

                for regex in reDict:
                    query = re.match(reDict[regex], data)
                    if query is not None:
                        if regex == 'getLocation':
                            device = query.group('device')
                            response = getLocation(device)
                        elif regex == 'setLocation':
                            device, location = query.groupdict().values()
                            setLocation(device, location)
                        elif regex == 'getZone':
                            device = query.group('device')
                            response = getZone(device)
                        elif regex == 'setZone':
                            device, zone = query.groupdict().values()
                            setZone(device, zone)
                        break

                if response != "":
                    self.serverPrint("Server sent: {}".format(response))
                    self.writeUTF(response)
            else:
                break

    def finish(self):
        self.serverPrint("connection with {} closed".format(
            self.client_address[0]))
        self.request.close()

    def readUTF(self):
        # get number of bytes to receive
        ready = select([self.request], [], [], timeout)
        if ready[0]:
            bytes_length = self.request.recv(2)
            try:
                utf_length = struct.unpack('!H', bytes_length)[0]
                return str(self.request.recv(utf_length), "utf-8")
            except struct.error:
                self.clientPrint("{} sent bad message header: {}".format(
                    self.client_address[0], bytes_length))
                return
            except UnicodeDecodeError as err:
                self.clientPrint("{} sent undecodable byte: {}".format(
                    self.client_address[0], err.object))
                return
        self.serverPrint("timeout: ", end='')

    def writeUTF(self, message):
        utf_length = struct.pack("!H", len(message))
        self.request.send(utf_length)  # send length of string
        self.request.send(message.encode("utf-8"))  # send string

    def serverPrint(self, string, end='\n'):
        lines = [string[i:i+40] for i in range(0, len(string), 40)]
        for line in lines[:-1]:
            print(Fore.RED + line + Style.RESET_ALL)
        print((Fore.RED + lines[-1] + Style.RESET_ALL), end=end)

    def clientPrint(self, string, end='\n'):
        try:
            clientType = knownClients[self.client_address[0]]['type']
            if clientType == 'self':
                color = Fore.YELLOW
            elif clientType == 'bigBrother':
                color = Fore.LIGHTBLUE_EX
            elif clientType == 'android':
                color = Fore.GREEN
        except:
            color = Fore.MAGENTA

        lines = [string[i:i+40] for i in range(0, len(string), 40)]
        for line in lines[:-1]:
            print(''.ljust(40), end='')
            print(color + line + Style.RESET_ALL)
        print(''.ljust(40), end='')
        print((color + lines[-1] + Style.RESET_ALL), end=end)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

    # def __init__(self, address, requestHandler):
    #     self.timeout = 10.0  # how long until connection is closed after not receiving any data
    #     self.tickrate = 50.00

    #     self.fileDir = "./data/"
    #     pathlib.Path(fileDir).mkdir(parents=True, exist_ok=True)

    #     # load/create knownClients
    #     try:
    #         with open(fileDir + 'knownClients.json') as clientFile:
    #             self.knownClients = json.load(clientFile)
    #     except FileNotFoundError:
    #         self.knownClients = {}

    #     # put all device files in a dict, create dict of associated mutex locks
    #     self.deviceFiles = {}
    #     for _, _, files in os.walk(fileDir):
    #         for file in files:
    #             if "BB_" in file:
    #                 self.deviceFiles[os.path.splitext(file)[0]] = self.fileDir + file
    #     self.deviceMutex = {}
    #     for device in deviceFiles:
    #         self.deviceMutex[device] = threading.Lock()

    #     super().__init__(address, requestHandler)


def client(ip, port, message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        def writeUTF(msg):
            sock.send(struct.pack("!H", len(msg)))
            sock.send(msg.encode("utf-8"))

        def clientPrint(string, end='\n'):
            lines = [string[i:i+40] for i in range(0, len(string), 40)]
            for line in lines:
                print(''.ljust(40), end='')
                print((Fore.YELLOW + line + Style.RESET_ALL).ljust(40), end=end)

        sock.connect((ip, port))
        writeUTF(message)
        if "get" in message:
            utf_length = struct.unpack('!H', sock.recv(2))[0]
            response = str(sock.recv(utf_length), "utf-8")
            clientPrint("Client Received: {}".format(response))
        writeUTF("Goodbye")


if __name__ == "__main__":
    if "win" in platform:
        # assign the server ip to your machine's local ip address.
        # I don't know whether any windows machines will be able to accept
        # connections from outside their local network or not but the local
        # client objects will still work for testing commands
        IP = socket.gethostbyname(socket.gethostname())
        knownClients[IP] = {'type': "self"}
    else:
        IP = ''
        knownClients['127.0.0.1'] = {'type': "self"}


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
        print("Press Enter to shutdown server: \n")

        """test server functions with client objects here"""
        # client(ip, port, "setLocation BB_2 0.324N,40.432E"); sleep(0.05)
        # client(ip, port, "getLocation BB_2"); sleep(0.05)
        # client(ip, port, "setZone BB_2 0.324N,40.432E,4.13"); sleep(0.05)
        # client(ip, port, "getZone BB_2"); sleep(0.05)

        try:
            shutdown = input()
            server.shutdown()
        except KeyboardInterrupt:
            print("Keyboard Interrupt, saving files...")

    with open(fileDir + 'knownClients.json', 'w+') as clientFile:
        json.dump(knownClients, clientFile, indent=4)

deinit()  # return stdin and stderr colors back to normal
