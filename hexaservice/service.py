#!/usr/bin/python3
import os
import sys
import time
import signal
import threading

import paho.mqtt.client as mqtt
from PIL import Image

import led_panel
from led_panel import panels, compile_image
from fontutil import base_font

DEBUG = False


class SimpleCache:
    def __init__(self):
        self.key = None
        self.value = None

    def get(self, key):
        if self.key == key:
            return self.value
        return None

    def set(self, key, value):
        self.key = key
        self.value = value


render_message_cache = SimpleCache()
render_time_bitmap_cache = SimpleCache()


def internet_time() -> float:
    """Granular Swatch Internet Time based on Biel Meridian (UTC+1)."""
    return (((time.time() + 3600) % 86400) * 1000) / 86400


def render_time_bitmap() -> bytes:
    """Render local time and Swatch beats into a 2-panel bitmap."""
    beats = internet_time()
    msg = time.strftime("%H:%M:%S")
    cached_result = render_message_cache.get(beats + msg)
    if cached_result:
        return cached_result
    txtimg = base_font.strImg(msg)
    img = Image.new("1", (120, 7))
    img.paste(txtimg, (15, 0))
    bmsg = f"{beats:06.2f}"
    txt2img = base_font.strImg(bmsg)
    img.paste(txt2img, (62, 0))
    img.paste(base_font.strImg(".beats"), (93, 0))
    bitmap = compile_image(img, 0, 0)
    render_message_cache.set(beats + msg, bitmap)
    return bitmap


def render_message_bitmap(msg: str, offset: int) -> bytes:
    """Render the given message with offset into a 2-panel bitmap."""
    cached_result = render_message_cache.get(message)
    if cached_result:
        return cached_result
    txtimg = base_font.strImg(msg)
    img = Image.new("1", (120, 7))
    img.paste(txtimg, (offset, 0))
    bitmap = compile_image(img, 0, 0)
    render_message_cache.set(message, bitmap)
    return bitmap


hlock = threading.Lock()
running = True
powered = True

TOPIC_PREFIX = "hexascroller"
TOPIC_POWER = f"{TOPIC_PREFIX}/power"
TOPIC_POWER_SET = f"{TOPIC_POWER}/set"
TOPIC_MESSAGE = f"{TOPIC_PREFIX}/message"
AVAILABILITY_TOPIC = f"{TOPIC_PREFIX}/available"


def on_connect(client: mqtt.Client, userdata, flags, rc):
    client.publish(TOPIC_POWER, b"ON", qos=0)
    client.publish(AVAILABILITY_TOPIC, "online")
    client.subscribe(TOPIC_POWER_SET, qos=0)
    client.subscribe(TOPIC_MESSAGE, qos=0)


def on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
    global powered
    global msg_until
    global msg_offset
    global message

    if msg.topic == TOPIC_POWER_SET:
        powered = msg.payload == b"ON"
        with hlock:
            panels[0].set_relay(powered)
        client.publish(TOPIC_POWER, msg.payload)
    elif msg.topic == TOPIC_MESSAGE:
        msg_offset = 0
        message = msg.payload.decode()
        msg_until = time.time() + 30.0


def mqtt_thread():
    global running
    global DEBUG

    host = os.environ.get("MQTT_BROKER", "mqttbroker.lan")
    user = os.environ.get("MQTT_USER")
    pw = os.environ.get("MQTT_PASS")

    if DEBUG:
        host = "localhost"
    client = mqtt.Client()
    client.enable_logger()
    client.on_connect = on_connect
    client.on_message = on_message
    if user:
        print(f"Logging into MQTT as {user}")
        client.username_pw_set(user, pw)
    client.connect(host, 1883, 60)
    client.loop_start()
    while running:
        time.sleep(1)
    client.publish(TOPIC_POWER, b"OFF", qos=0)
    client.publish(AVAILABILITY_TOPIC, "offline")
    client.loop_stop()
    client.disconnect()


print(f"NAME {__name__}")

msg_until = None
msg_offset = 0.0
message = None


def panel_thread():
    global running
    global powered
    global msg_until
    global msg_offset
    global message
    while running:
        if powered:
            if msg_until:
                bitmap = render_message_bitmap(message, 0)
                if time.time() > msg_until:
                    msg_until = None
                    message = None
            else:
                bitmap = render_time_bitmap()
            with hlock:
                for j in range(3):
                    panels[j].set_compiled_image(bitmap)
            time.sleep(0.06)
        else:
            time.sleep(0.25)
    panels[0].set_relay(False)

    led_panel.shutdown()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        DEBUG = True

    if not led_panel.init(DEBUG):
        print("Could not find all three panels; aborting.")
        sys.exit(0)
    panels[0].set_relay(True)

    def sigint_handler(signal, frame):
        global running
        print("Caught ctrl-C; shutting down.")
        running = False

    signal.signal(signal.SIGINT, sigint_handler)

    def sigterm_handler(signal, frame):
        global running
        running = False

    signal.signal(signal.SIGTERM, sigterm_handler)
    tm = threading.Thread(target=mqtt_thread)
    t = threading.Thread(target=panel_thread)
    t.start()
    tm.start()
    t.join()
