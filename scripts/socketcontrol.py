#!/usr/bin/python

import serial
import re
import time
import sys
import simplejson
import popen2
import socket

class Monitor:
    def __init__(self):
        self.serialPort = None

    def open(self,portName,baud=9600):
        self.serialPort = serial.Serial(portName, baud, timeout=3.5)
        try:
            self.serialPort.open()
        except serial.SerialException, e:
            sys.stderr.write("Could not open serial port %s: %s\n" % (self.serialPort.portstr, e)
)
        time.sleep(1.1)
        self.serialPort.write("+++")
        time.sleep(1.1)
        self.serialPort.write("ATPL2\r")
        time.sleep(0.03)
        self.serialPort.write("ATMY2\r")
        time.sleep(0.03)
        self.serialPort.write("ATDL1\r")
        time.sleep(0.03)
        self.serialPort.write("ATSM0\r")
        time.sleep(0.03)
        self.serialPort.write("ATCN\r")
        time.sleep(0.03)
        data = self.serialPort.read(1)  # read one, blocking
        n = self.serialPort.inWaiting() # look if there is more
        if n:
            data = data + self.serialPort.read(n)
        print "DATA: ", data

mon = Monitor()
mon.open("/dev/ttyUSB0")

def sendToClient(client,data):
    global mon
    if data: 
        client.send("Got: %s\n"%(data))
        mon.serialPort.flushInput()
        mon.serialPort.write(data + "\n")
        resp = mon.serialPort.read(1)
        n = mon.serialPort.inWaiting()
        timeout = 3.0
        while timeout > 0.0 and resp.find("\n") == -1:
            n = mon.serialPort.inWaiting()
            resp = resp + mon.serialPort.read(n)
            time.sleep(0.2)
            timeout = timeout - 0.2
        client.send("Response:")
        client.send(resp.strip())
        client.send("\n") 

host = '' 
port = 666 
backlog = 5 
size = 1024 
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
s.bind((host,port)) 
s.listen(backlog) 
while 1: 
    client, address = s.accept()
    client.send("Write a message to be HEXASCROLLED:\n")
    data = client.recv(size) 
    data = data.strip()
    sendToClient(client,data)
    # flash lights if standard message
    if data and data[0] != '!':
        sendToClient(client,"!A0");
    client.close()
