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

def compile_image(img, x=0, y=0):
    bitmap = ''
    width = min(img.size[0]-x,120)
    height = min(7,img.size[1]-y)
    for i in range(width):
        b = 0
        for j in range(height):
            if img.getpixel(( i+x, j+y )):
                b |= 1 << (7-j)
            bitmap = bitmap + struct.pack("B",b)
    return bitmap

class Panel:
    def __init__(self):
        self.serialPort = None

    def open(self,portName,baud=9600):
        self.serialPort = serial.Serial(portName, baud, timeout=0.5)
        try:
            self.serialPort.open()
        except serial.SerialException as e:
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

    def setRelay(self, on):
        if on:
            self.command(CC_RELAY,struct.pack("B",1),0)
        else:
            self.command(CC_RELAY,struct.pack("B",0),0)

    def setMessage(self, message, x =0, y =0):
        message = message[:120]        
        cmd = struct.pack("bb",x,y)+message
        self.command(CC_TEXT,cmd,0)

    def setImage(self, img, x =0, y =0):
        self.command(CC_BITMAP,compile_image(img,x,y),0)


    def setCompiledImage(self, bitmap):
        self.command(CC_BITMAP,bitmap,0)

    def getID(self):
        v = self.command(CC_GET_ID,"",1)
        id = ord(v[0])
        return id


panels = [None]*3

def init():
    for port in range(0,3):
        name = "/dev/ttyACM{0}".format(port)
        p = Panel()
        p.open(name)
        panels[p.getID()] = p

def shutdown():    
    for p in panels:
        p.close()





