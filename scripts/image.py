#!/usr/bin/python

import serial
import sys
import struct
import time

from PIL import Image


class Monitor:
    def __init__(self):
        self.serialPort = None

    def open(self, portName, baud=9600):
        self.serialPort = serial.Serial(portName, baud, timeout=10)
        try:
            self.serialPort.open()
        except serial.SerialException, e:
            sys.stderr.write(
                "Could not open serial port %s: %s\n" % (self.serialPort.portstr, e)
            )

    def close(self):
        self.serialPort.close()


mon = [Monitor(), Monitor(), Monitor()]
mon[0].open("/dev/ttyACM0")
mon[1].open("/dev/ttyACM1")
mon[2].open("/dev/ttyACM2")


def show(x, y, img):
    s = ""
    for i in range(120):
        n = 0
        for j in range(7):
            v = img.getpixel((i + x, j + y))
            if v:
                n |= 1 << (7 - j)
        s = s + struct.pack("B", n)
    for m in mon:
        m.serialPort.write(struct.pack("BB", 0xA2, 120))
        m.serialPort.write(s)
        rsp = m.serialPort.read(2)
        ok = len(rsp) == 2 and rsp[0] == "\x00" and rsp[1] == "\x00"
        if not ok:
            print("Did not receive correct response!")
            print("Response: " + ",".join(map(lambda x: hex(ord(x)), rsp)))


x = 0
y = 0
img = Image.open("test.png").convert("1")
if len(sys.argv) > 3:
    x = int(sys.argv[1])
    y = int(sys.argv[2])
    img = Image.open(sys.argv[3]).convert("1")

for y in range(img.size[1] - 7):
    show(x, y, img)
    time.sleep(0.05)

mon.close()
