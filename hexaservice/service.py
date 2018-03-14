#!/usr/bin/python3
import led_panel
from led_panel import panels, compile_image
from fontutil import base_font
from PIL import Image
import time
import signal
import sys
import threading
import os
import paho.mqtt.client as mqtt

debug = False

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

hlock = threading.Lock()
running = True
powered = True

TOPIC_PRE = '/hexascroller/power'

def on_connect(client, userdata, flags, rc):
    #print("CONNECTED")
    #client.subscribe("$SYS/#")
    client.publish(TOPIC_PRE+'/state',b'ON',qos=0)
    client.subscribe(TOPIC_PRE+'/command',qos=0)
    #print("RV: {}".format(rv))

def on_message(client, userdata, msg):
    global powered
    #print("MESSAGE: {}".format(msg.payload))
    powered = msg.payload == b'ON'
    hlock.acquire()
    panels[0].setRelay(powered)
    hlock.release()
    client.publish(TOPIC_PRE+'/state',msg.payload)


def mqtt_thread():
    global running
    global debug
    host = 'automation.local'
    if debug:
        host = 'localhost'
    token = os.environ.get('FLESPI_TOKEN')
    client = mqtt.Client('bogus-id')
    client.enable_logger()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host,1883,60)
    while running:
        client.loop()
    client.publish(TOPIC_PRE+"/state",b'OFF',qos=0)
    client.disconnect()

print("NAME {}".format(__name__))

def panel_thread():
    global running
    global powered
    while running:
        if powered:
            bitmap = render_time_bitmap()
            hlock.acquire()
            for j in range(3):
                panels[j].setCompiledImage(bitmap)
            hlock.release()
            time.sleep(0.06) 
        else:
            time.sleep(0.25)
    panels[0].setRelay(False)

    led_panel.shutdown()

if __name__=="__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'debug':
        debug = True

    if not led_panel.init(debug):
        print("Could not find all three panels; aborting.")
        sys.exit(0)
    panels[0].setRelay(True)
    
    def sigint_handler(signal,frame):
        global running
        print("Caught ctrl-C; shutting down.")
        running = False

    signal.signal(signal.SIGINT,sigint_handler)

    def sigterm_handler(signal,frame):
        global running
        running = False

    signal.signal(signal.SIGTERM,sigterm_handler)
    tm = threading.Thread(target=mqtt_thread)
    t = threading.Thread(target=panel_thread)
    t.start()
    tm.start()    
    t.join()
