#!/usr/bin/python

import serial
import re
import time
import sys
import simplejson
import popen2
import struct

class Monitor:
    def __init__(self):
        self.serialPort = None

    def open(self,portName,baud=9600):
        self.serialPort = serial.Serial(portName, baud, timeout=10)
        try:
            self.serialPort.open()
        except serial.SerialException, e:
            sys.stderr.write("Could not open serial port %s: %s\n" % (self.serialPort.portstr, e))
    def close(self):
        self.serialPort.close()

mon = Monitor()
mon.open("/dev/ttyACM0")

if len(sys.argv) > 1:
    s = " ".join(sys.argv[1:])
    s = s[:120]
    mon.serialPort.write(struct.pack("BBbb",0xA1,len(s)+2,0,0))
    mon.serialPort.write(s)

mon.close()




