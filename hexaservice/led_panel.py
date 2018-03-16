#!/usr/bin/python3

import serial
import sys
import struct
import random
import functools

CC_TEXT = 0xA1
CC_BITMAP = 0xA2
CC_SET_ID = 0xA3
CC_GET_ID = 0xA4
CC_UART = 0xA5
CC_RELAY = 0xA6

def compile_image(img, x=0, y=0):
    bitmap = b''
    width = min(img.size[0]-x,120)
    height = min(7,img.size[1]-y)

    for i in range(width):
        b = 0
        for j in range(height): # vertical scanning? jerk
            if img.getpixel(( i+x, j+y )):
                b |= 1 << (7-j)
        bitmap = bitmap + struct.pack("B",b)
    return bitmap

class Panel:
    def __init__(self, debug=False):
        self.serialPort = None
        
        if debug is not False:
            self.debug = True
            self.id = debug
        else:
            self.debug = False

    def open(self,portName,baud=9600):
        if self.debug: 
            import socket            
            print("Opening UDP socket to localhost : {}".format(portName))
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.port = portName

        else:
            self.serialPort = serial.Serial(portName, baud, timeout=0.5)
            try:
                self.serialPort.open()
            except serial.serialutil.SerialException as se:
                sys.stderr.write("Serial port autoopened, probably ok. {}\n".format(se))
            except serial.SerialException as e:
                sys.stderr.write("Could not open serial port {}: {}\n".format(self.serialPort.portstr, e))


    def command(self,command,payload,expected):
        l = len(payload)
        packet = struct.pack("BB",command,l)
        if l > 0:
            packet = packet + payload
        if self.debug: 
            self.sock.sendto(packet, ("127.0.0.1", self.port))
            return
        self.serialPort.write(packet)
        rsp = self.serialPort.read(2)
        if len(rsp) < 2 or rsp[0] != 0:
            #print("Error on panel {1} command {0}".format(command,self.id))
            if len(rsp) == 2:
                epl = rsp[1]
                if epl > 0: rsp = rsp + self.serialPort.read(epl)
            #print("Rsp length {0}, {1}".format(len(rsp),rsp))
            return ""
        l = rsp[1]
        rpay = self.serialPort.read(l)
        return rpay

    def close(self):
        if self.debug: return
        self.serialPort.close()

    def setRelay(self, on):
        if on:
            self.command(CC_RELAY,struct.pack("B",1),0)
            print("Relay on")
        else:
            print("Relay off")
            self.command(CC_RELAY,struct.pack("B",0),0)

    def setMessage(self, message, x =0, y =0):
        message = message[:100]        
        cmd = struct.pack("bb",x,y)+message
        self.command(CC_TEXT,cmd,0)

    def setImage(self, img, x =0, y =0):
        self.command(CC_BITMAP,compile_image(img,x,y),0)


    def setCompiledImage(self, bitmap):
        self.command(CC_BITMAP,bitmap,0)

    def getID(self):
        if self.debug: return self.id

        v = self.command(CC_GET_ID,"",1)
        self.id = v[0]
        print("ID'd panel {0}".format(self.id))
        return self.id


panels = [None]*3
import glob
import time

def init(debug = False):
    if debug: 
        for port_num in range(0,3):
            port = 9990 + port_num
            p = Panel(port_num)
            p.open(port)
            panels[port_num] = p
            time.sleep(0.1)
        return True

    else: 
        for candidate in glob.glob('/dev/ttyACM*'):
            p = Panel()
            try:
                print("Opening candidate {}".format(candidate))
                p.open(candidate)
                panels[p.getID()] = p
                print("{} succeeded".format(candidate))
            except Exception as e:
                p.close()
                print("{} failed".format(candidate))
        return functools.reduce(lambda a,b: a & (b != None), panels, True)

def shutdown():    
    for p in panels:
        p.close()





