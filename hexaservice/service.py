#!/usr/bin/python
import led_panel
from led_panel import panels
from font_util import basic_font
from PIL import Image
import time
import signal
import sys

class ServiceThread:
    pass

if __name__=="__main__":
    led_panel.init()
    panels[0].setRelay(True)
    def sigint_handler(signal,frame):
	print("Caught ctrl-C; shutting down.")
	panels[0].setRelay(False)
        led_panel.shutdown()
        sys.exit(0)
    signal.signal(signal.SIGINT,sigint_handler)
    while True:
        msg = time.strftime("%H:%M:%S")
        for j in range(3):
            txtimg = base_font.strImg(msg)
            img = Image.new("1",(120,7))
            img.paste(txtimg,(15,0))
            img.paste(txtimg,(75,0))
            panels[j].setImage(img,0,0)
        time.sleep(0.1)

    panels[0].setRelay(False)

    led_panel.shutdown()
