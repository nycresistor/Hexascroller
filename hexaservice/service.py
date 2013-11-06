#!/usr/bin/python
import led_panel
from led_panel import panels, compile_image
from fontutil import base_font
from PIL import Image
import time
import signal
import sys
import threading

debug = False



def internet_time():
    "Swatch Internet Time. Biel meridian."
    h, m, s = time.gmtime()[3:6]
    h += 1 # Biel time zone: UTC+1
    print h,m,s
    seconds = s + (60.0*m) + (60.0*60.0*h)
    beats = seconds * 1000.0 / (60.0*60.0*24.0)
    beats = beats % 1000.0
    return beats

class PanelThread(threading.Thread):
    def __init__(self, panel):
        pass

class ServiceThread:
    pass


if __name__=="__main__":

    if len(sys.argv) > 1 and sys.argv[1] == 'debug':
        debug = True

    led_panel.init(debug)
    panels[0].setRelay(True)
    
    def sigint_handler(signal,frame):
        print("Caught ctrl-C; shutting down.")
        panels[0].setRelay(False)
        led_panel.shutdown()
        sys.exit(0)
    signal.signal(signal.SIGINT,sigint_handler)

    while True:
        beats = internet_time()
        msg = time.strftime("%H:%M:%S")
        txtimg = base_font.strImg(msg)
        img = Image.new("1",(120,7))
        img.paste(txtimg,(15,0))
        bmsg = "{0:3.2f} .beats".format(beats)
        txt2img = base_font.strImg(bmsg)
        img.paste(txt2img,(75,0))
        bitmap = compile_image(img,0,0)

        for j in range(3):
            panels[j].setCompiledImage(bitmap)
        time.sleep(0.1)

    panels[0].setRelay(False)

    led_panel.shutdown()
