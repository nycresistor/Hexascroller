#!/usr/bin/python
import led_panel
from led_panel import panels, compile_image
from fontutil import base_font
from PIL import Image
import time
import signal
import sys
import threading
import Queue
import socket
import multiprocessing
import select

debug = False

host = ''
port = 50000

bitmapGeneratorUnits = []
unitQueue = []

defaultUnitNum = 0 # first unit in bitmapGeneratorUnits
currentUnitNum = 0

class MessageUnit():
    def __init__(self, messageQueue):
        self.running = False
        self.waitingToRun = False
        self.timeout = 5
        self.message = None
        self.messageQueue = messageQueue
        self.priority = 1
        self.xOffset = 120
        self.txtimg = None
        self.scrollSpeed = 0.05

    def render_message(self):
        
        if self.txtimg is None:
            self.txtimg = base_font.strImg(self.message)

        img = Image.new("1",(120,7))
        img.paste(self.txtimg,(self.xOffset,0))
        bitmap = compile_image(img,0,0)
        return bitmap

    def check_messages(self):
        try:
            data = self.messageQueue.get(True, 0)
            print "Got data to scroll: %s" % data
            return data

        except Queue.Empty:
            return

    def begin(self):
        self.startTime = time.time()

    def run(self):
        self.waitingToRun = False

        if self.done(): 
            self.cleanup()
            return

        bitmap = self.render_message()

        self.xOffset -= 1

        time.sleep(self.scrollSpeed)

        return bitmap

    def done(self):
        # if time.time() - self.startTime > self.timeout:
        #     return True

        if self.txtimg is None: return False
        if self.xOffset < -self.txtimg.size[0]:
            return True


    def cleanup(self):
        self.message = None
        self.running = False
        self.xOffset = 120
        self.txtimg = None

    def waiting(self):
        if self.waitingToRun: return True

        message = self.check_messages()
        if message:
            self.message = message
            self.waitingToRun = True
            return True

class TimeUnit():
    def __init__(self):
        self.priority = 99

    def run(self):
        time.sleep(0.1)
        return self.render_time_bitmap()

    def render_time_bitmap(self):
        "Render local time + Swatch beats into a 2-panel bitmap"
        beats = self.internet_time2()

        msg = time.strftime("%H:%M:%S")
        txtimg = base_font.strImg(msg)
        img = Image.new("1",(120,7))
        img.paste(txtimg,(15,0))
        bmsg = "{0:03.2f}".format(beats)
        txt2img = base_font.strImg(bmsg)
        img.paste(txt2img,(62,0))
        img.paste(base_font.strImg(".beats"),(93,0))
        bitmap = compile_image(img,0,0)

        return bitmap

    def internet_time2(self):
        "More granular Swatch time. Courtesy https://github.com/gcohen55/pebble-beapoch"
        return (((time.time() + 3600) % 86400) * 1000) / 86400

    def stillRunning(self):
        return True

    def waiting(self):
        return False

class PanelThread(threading.Thread):
    def __init__(self, bitmapQueue):
        super(PanelThread, self).__init__()
        self.bitmapQueue = bitmapQueue
        self.stoprequest = threading.Event()

    def run(self):

        while not self.stoprequest.isSet():
            try:
                bitmap = self.bitmapQueue.get(True, 0.05)
                for j in range(3):
                    panels[j].setCompiledImage(bitmap)
        
            except Queue.Empty:
                continue

    def join(self, timeout=None):
        print "Leaving panel thread"
        self.stoprequest.set()
        super(PanelThread, self).join(timeout)

class ServiceThread(threading.Thread):
    def __init__(self, messageQueue):
        super(ServiceThread, self).__init__()
        self.messageQueue = messageQueue
        self.stoprequest = threading.Event()

    def run(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(5)
        print "Listening on port %s" % port

        while not self.stoprequest.isSet():
            
            rr, rw, err = select.select([server_socket], [], [], 1)
            if rr:

                sockfd, addr = server_socket.accept()
                data = sockfd.recv(1024)
                if data:
                    self.messageQueue.put(data)
                sockfd.close()

    def join(self, timeout=None):
        print "Leaving service thread"
        self.stoprequest.set()
        super(ServiceThread, self).join(timeout)

def sigint_handler(signal,frame):
        print("Caught ctrl-C; shutting down.")
        panelThread.join()
        serviceThread.join()
        panels[0].setRelay(False)
        led_panel.shutdown()
        sys.exit(0)

if __name__=="__main__":

    if len(sys.argv) > 1 and sys.argv[1] == 'debug':
        debug = True

    led_panel.init(debug)
    panels[0].setRelay(True)

    bitmapQueue = Queue.Queue()
    panelThread = PanelThread(bitmapQueue=bitmapQueue)

    messageQueue = Queue.Queue()

    serviceThread = ServiceThread(messageQueue=messageQueue)
    serviceThread.daemon = True
    serviceThread.start()
    
    signal.signal(signal.SIGINT,sigint_handler)

    panelThread.start()

    bitmapGeneratorUnits.append(TimeUnit())
    bitmapGeneratorUnits.append(MessageUnit(messageQueue))

    currentUnit = TimeUnit()

    while True:

        bitmap = None

        for unit in bitmapGeneratorUnits:
            if unit.waiting() and unit.priority < currentUnit.priority:
                currentUnit = unit
                currentUnit.begin()

        bitmap = currentUnit.run()
        if bitmap is None:
            currentUnit = TimeUnit()
            continue
        
        bitmapQueue.put(bitmap)

    panelThread.join()
    serviceThread.join()
    panels[0].setRelay(False)

    led_panel.shutdown()