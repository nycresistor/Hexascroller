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

generatorUnits = []
unitQueue = []

defaultUnitNum = 0 # first unit in bitmapGeneratorUnits
currentUnitNum = 0

messageLoops = 3

class ThingToDisplay():
	bitmap = 0
	text = 1

	def __init__(self, thingType, thing, x=0, y=0):
		self.thingType = thingType
		self.thing = thing
		self.x = x
		self.y = y

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
        self.scrollSpeed = 0.04
        self.loops = 0

    def render_message(self):
        
        # self.startTime = time.time()
        # if self.txtimg is None:
        #     self.txtimg = base_font.strImg(self.message)

        # img = Image.new("1",(300,7))
        # img.paste(self.txtimg,(self.xOffset,0))
        # bitmap = ThingToDisplay(ThingToDisplay.bitmap, compile_image(img,0,0))

        thing = ThingToDisplay(ThingToDisplay.text, self.message, self.xOffset, 0)

        # if debug: print "Rendering took %f" % (time.time() - startTime)
        return thing

    def check_messages(self):
        try:
            data = self.messageQueue.get(True, 0)
            print len(data)
            if len(data) > 36:
            	print "Data too long: %s (%s)" % (data, len(data))
            	return
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

        self.xOffset -= 1

        time.sleep(self.scrollSpeed)

        thing = self.render_message()

        return thing

    def done(self):
        # if time.time() - self.startTime > self.timeout:
        #     return True

        # if self.txtimg is None: return False
        # if self.xOffset < -self.txtimg.size[0]:
        #     return True

        if self.xOffset < -127:
            if self.loops == messageLoops:
                self.loops = 0
                return True
            else:
                self.loops += 1
                self.xOffset = 120
        return False

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
        bitmap = ThingToDisplay(ThingToDisplay.bitmap, compile_image(img,0,0))

        return bitmap

    def internet_time2(self):
        "More granular Swatch time. Courtesy https://github.com/gcohen55/pebble-beapoch"
        return (((time.time() + 3600) % 86400) * 1000) / 86400

    def stillRunning(self):
        return True

    def waiting(self):
        return False

class PanelThread(threading.Thread):
    def __init__(self, stuffToDisplay):
        super(PanelThread, self).__init__()
        self.stuffToDisplay = stuffToDisplay
        self.stoprequest = threading.Event()

    def run(self):

        while not self.stoprequest.isSet():
            
            try:
                thingToDisplay = self.stuffToDisplay.get(True, 0.05)

                if thingToDisplay.thingType == ThingToDisplay.bitmap:
                    for j in range(3):
                        panels[j].setCompiledImage(thingToDisplay.thing)
                        if (debug): time.sleep(0.01)
                elif thingToDisplay.thingType == ThingToDisplay.text:
                    for j in range(3):
	                    panels[j].setMessage(thingToDisplay.thing, thingToDisplay.x, thingToDisplay.y)
        
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
                sockfd.send("Enter a message to send. 36 chars max.\n")
                data = sockfd.recv(1024)
                if data:
                    if len(data) > 36:
                        sockfd.send("The message is too long! What's wrong with you?\n")
                    else:
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

    stuffToDisplay = Queue.Queue()
    panelThread = PanelThread(stuffToDisplay=stuffToDisplay)

    messageQueue = Queue.Queue()
    serviceThread = ServiceThread(messageQueue=messageQueue)
    serviceThread.daemon = True
    serviceThread.start()
    
    signal.signal(signal.SIGINT,sigint_handler)

    panelThread.start()

    generatorUnits.append(TimeUnit())
    generatorUnits.append(MessageUnit(messageQueue))

    currentUnit = TimeUnit()

    while True:

        bitmap = None

        for unit in generatorUnits:
            if unit.waiting() and unit.priority < currentUnit.priority:
                print "%s ready" % unit
                currentUnit = unit
                currentUnit.begin()

        thingToDisplay = currentUnit.run()
        if thingToDisplay is None:
            currentUnit = TimeUnit()
            continue
        
        stuffToDisplay.put(thingToDisplay)



    # for x in xrange(120, -120, -1):
    #     for panel in panels:
    #         panel.setMessage("test", x)

    panelThread.join()
    serviceThread.join()
    panels[0].setRelay(False)

    led_panel.shutdown()