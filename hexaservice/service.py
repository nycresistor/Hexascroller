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

MODE_TIME = 0
MODE_MESSAGE = 1

mode = MODE_TIME

messagesToScroll = []

def internet_time():
    "Swatch Internet Time. Biel meridian."
    h, m, s = time.gmtime()[3:6]
    h += 1 # Biel time zone: UTC+1
    seconds = s + (60.0*m) + (60.0*60.0*h)
    beats = seconds * 1000.0 / (60.0*60.0*24.0)
    beats = beats % 1000.0
    return beats

def internet_time2():
    "More granular Swatch time. Courtesy https://github.com/gcohen55/pebble-beapoch"
    return (((time.time() + 3600) % 86400) * 1000) / 86400

def render_time_bitmap():
    "Render local time + Swatch beats into a 2-panel bitmap"
    beats = internet_time2()
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

def render_message():
    msg = messagesToScroll[0]
    txtimg = base_font.strImg(msg)
    img = Image.new("1",(120,7))
    img.paste(txtimg,(15,0))
    bitmap = compile_image(img,0,0)

    return bitmap

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
        # server_socket.settimeout(1)
        server_socket.listen(5)
        print "Listening on port %s" % port

        while not self.stoprequest.isSet():
            
            rr, rw, err = select.select([server_socket], [], [], 1)
            if rr:

                sockfd, addr = server_socket.accept()
                data = sockfd.recv(1024)
                if data:
                    self.messageQueue.put(data)
                else:
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

    while True:

        try:
            data = messageQueue.get(True, 0)
            print "Got data to scroll: %s" % data
            messagesToScroll.append(data)
            mode = MODE_MESSAGE

        except Queue.Empty:
            pass

        if mode == MODE_TIME:
            bitmapQueue.put(render_time_bitmap())
        elif mode == MODE_MESSAGE:
            bitmapQueue.put(render_message())



        time.sleep(0.1)

        


    # panelThread.join()

    panels[0].setRelay(False)

    led_panel.shutdown()
