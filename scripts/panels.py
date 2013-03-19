#!/usr/bin/python

import serial
import sys
import struct

CC_TEXT = 0xA1
CC_BITMAP = 0xA2
CC_SET_ID = 0xA3
CC_GET_ID = 0xA4
CC_UART = 0xA5
CC_RELAY = 0xA6

class Panel:
    def __init__(self):
        self.serialPort = None

    def open(self,portName,baud=9600):
        self.serialPort = serial.Serial(portName, baud, timeout=0.5)
        try:
            self.serialPort.open()
        except serial.SerialException, e:
            sys.stderr.write("Could not open serial port %s: %s\n" % (self.serialPort.portstr, e))

    def command(self,command,payload,expected):
        l = len(payload)
        self.serialPort.write(struct.pack("BB",command,l))
        if l > 0:
            self.serialPort.write(payload)
        rsp = self.serialPort.read(2)
        if len(rsp) < 2 or ord(rsp[0]) != 0:
            print("Error on command {0}".format(command))
            return ""
        l = ord(rsp[1])
        rpay = self.serialPort.read(l)
        return rpay

    def close(self):
        self.serialPort.close()

panels = [None]*3
for port in range(0,3):
    name = "/dev/ttyACM{0}".format(port)
    p = Panel()
    p.open(name)
    v = p.command(CC_GET_ID,"",1)
    id = ord(v[0])
    panels[id] = p

panels[0].command(CC_RELAY,struct.pack("B",1),0)
    
for p in panels:
    p.close()





