#!/usr/bin/python

import serial
import sys
import struct


class Monitor:
    def __init__(self):
        self.serialPort = None

    def open(self, portName, baud=9600):
        self.serialPort = serial.Serial(portName, baud, timeout=0.5)
        try:
            self.serialPort.open()
        except serial.SerialException, e:
            sys.stderr.write(
                "Could not open serial port %s: %s\n" % (self.serialPort.portstr, e)
            )

    def close(self):
        self.serialPort.close()


mon = Monitor()
mon.open("/dev/ttyACM0")

if len(sys.argv) > 1:
    id = int(sys.argv[1])
    print("Setting ID to {0}".format(id))
    mon.serialPort.write(struct.pack("BBB", 0xA3, 1, id))
    rsp = mon.serialPort.read(2)
    ok = len(rsp) == 2 and rsp[0] == "\x00" and rsp[1] == "\x00"
    if not ok:
        print("Did not receive correct response!")
        print("Response: " + ",".join(map(lambda x: hex(ord(x)), rsp)))
else:
    mon.serialPort.write(struct.pack("BB", 0xA4, 0))
    rsp = mon.serialPort.read(3)
    ok = len(rsp) == 3 and rsp[0] == "\x00" and rsp[1] == "\x01"
    # ok = len(rsp) == 3 and rsp[0] == '\x00' and rsp[1] == '\x01'
    if not ok:
        print("Did not receive correct response!")
        print("Response: " + ",".join(map(lambda x: hex(ord(x)), rsp)))
    else:
        id = ord(rsp[2])
        print("Got ID {0}".format(id))

mon.close()
