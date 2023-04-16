#!/usr/bin/python3
"""This program is a service that controls the hexascroller LED panel display, rendering
messages and time information. It communicates with an MQTT broker to receive commands and
updates from other devices or applications. The LED panel displays messages or local time
and Swatch Internet Time. When a new message is received, it is displayed on the panel, and
after a specified period (MSG_DURATION), the display reverts to showing the time.

The mqtt topics this service subscribes to are as follows:

- hexascroller/power/set: set the power state of the display.
  The payload should be "ON" or OFF"
- hexascroller/invert/set: set the invert state of the display.
  The payload should be "ON" or OFF"
- hexascroller/message: set the message to display.
  The payload should be a string of text to display.

The mqtt topics this service publishes to are as follows:

- hexascroller/power: the current power state of the display.
    The payload will be "ON" or OFF"
- hexascroller/invert: the current invert state of the display.
    The payload will be "ON" or OFF"

The service also publishes an availability topic:

- hexascroller/available: the availability of the service.
    The payload will be "online" or "offline"

"""

import os
import sys
import time
import signal
import threading
import logging
from typing import Optional
import dataclasses

import paho.mqtt.client as mqtt
from PIL import Image

from led_panel import (
    panels,
    compile_image,
    PANEL_WIDTH,
    PANEL_HEIGHT,
    init_panel,
    shutdown_panel,
)
from fontutil import base_font

logging.basicConfig(level=logging.DEBUG if "debug" in sys.argv else logging.INFO)
logger = logging.getLogger(__name__)

DEBUG = False
MSG_DURATION: float = 30.0
TOPIC_PREFIX: str = "hexascroller"
TOPIC_POWER: str = f"{TOPIC_PREFIX}/power"
TOPIC_POWER_SET: str = f"{TOPIC_POWER}/set"
TOPIC_INVERT: str = f"{TOPIC_PREFIX}/invert"
TOPIC_INVERT_SET: str = f"{TOPIC_INVERT}/set"
TOPIC_MESSAGE: str = f"{TOPIC_PREFIX}/message"
TOPIC_AVAILABILITY: str = f"{TOPIC_PREFIX}/available"

hlock = threading.Lock()


@dataclasses.dataclass
class State:
    # pylint: disable=too-few-public-methods,too-many-instance-attributes
    """
    Represents the state of a hexascroller LED panel display service. The service controls the panel
    display, rendering messages and time information, and communicates with an MQTT broker to
    receive commands and updates.

    This is a simple data class or struct class that only stores state. It has no methods.

    Attributes:
    -----------
    running : bool
        A boolean value indicating whether the service is running or not.
    powered : bool
        A boolean value indicating whether the LED panel display is powered on or not.
    inverted : bool
        A boolean value indicating whether the LED panel display is inverted or not.
    msg_until : Optional[float]
        The time (in seconds since epoch) until the current message should be displayed.
        If the value is 0.0, the message should not be displayed.
    msg_offset : float
        Represents the horizontal offset for scrolling the displayed message, if applicable.
        Set dynamically based on the message length, the scroll interval and the current time.
    message : Optional[str]
        A string representing the current message to be displayed.
        Set through the MQTT message topic.
    scroll_interval : float
        Represents the time interval (in seconds) between successive horizontal scrolling steps.
        Set dynamically based on the length of the message.
    """

    def __init__(self):
        self.bitmap: bytes = b"\0" * PANEL_WIDTH
        self.running: bool = True
        self.powered: bool = True
        self.inverted: bool = False
        self.msg_until: Optional[float] = None
        self.msg_offset: float = 0.0
        self.message: Optional[str] = None
        self.scroll_interval: float = 0.0


state = State()


class SimpleCache:
    """A simple cache for storing key-value pairs. This is used to cache rendered images.

    This is a very simple cache implementation that only stores a single key-value pair.
    It is used to cache rendered images, so that the same image is not rendered multiple
    times. This is not a very efficient cache implementation, but it is sufficient for
    the purposes of this application. Old images are simply overwritten by new ones, but
    this is not a problem because the strings are typically only used once, or very rarely.
    """

    def __init__(self):
        self.key = None
        self.value = None

    def get(self, key):
        """Retrieve a value from the cache by key."""
        if self.key == key:
            return self.value
        return None

    def set(self, key, value):
        """Store a key-value pair in the cache."""
        self.key = key
        self.value = value


render_cache = SimpleCache()


def internet_time() -> float:
    """Granular Swatch Internet Time based on Biel Meridian (UTC+1)."""
    return (((time.time() + 3600) % 86400) * 1000) / 86400


def render_time_bitmap() -> bytes:
    """Render local time and Swatch beats into a 2-panel bitmap."""
    beats = internet_time()
    msg = time.strftime("%H:%M:%S")
    bmsg = f"{beats:06.2f}"
    cached_result = render_cache.get(bmsg + msg)
    if cached_result:
        return cached_result
    img = Image.new("1", (PANEL_WIDTH, PANEL_HEIGHT))
    txtimg = base_font.string_image(msg)
    img.paste(txtimg, (15, 0))
    txtimg = base_font.string_image(f"{bmsg} .beats")
    img.paste(txtimg, (62, 0))
    bitmap = compile_image(img, 0, 0)
    render_cache.set(bmsg + msg, bitmap)
    return bitmap


def render_text_bitmap(text: str, offset: int) -> bytes:
    """Render the given text with offset into a 2-panel bitmap."""
    cached_result = render_cache.get(text)
    if cached_result:
        return cached_result
    txtimg = base_font.string_image(text)
    img = Image.new("1", (PANEL_WIDTH, PANEL_HEIGHT))
    img.paste(txtimg, (offset, 0))
    bitmap = compile_image(img, 0, 0)
    render_cache.set(text, bitmap)
    return bitmap


def on_mqtt_connect(client: mqtt.Client, userdata, flags, resultcode):
    """Callback function when the MQTT client connects to the broker."""
    power_state = b"ON" if state.powered else b"OFF"
    invert_state = b"ON" if state.inverted else b"OFF"

    logger.info(
        "MQTT client connected, flags %s, result code %s, user data %s",
        flags,
        resultcode,
        userdata,
    )
    client.publish(TOPIC_AVAILABILITY, "online")
    client.publish(TOPIC_POWER, power_state, qos=0)
    client.publish(TOPIC_INVERT, invert_state, qos=0)
    client.subscribe(TOPIC_POWER_SET, qos=0)
    client.subscribe(TOPIC_MESSAGE, qos=0)
    client.subscribe(TOPIC_INVERT_SET, qos=0)


def on_mqtt_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
    """Callback function when the MQTT client receives a message."""
    logger.info("MQTT message received: %s, user data %s", msg.topic, userdata)
    if msg.topic == TOPIC_MESSAGE:
        state.msg_offset = 0
        state.message = msg.payload.decode()
        logger.info("Message received: %s", state.message)
        state.msg_until = time.time() + MSG_DURATION

        # Calculate scroll interval based on the width of the message
        message_width = base_font.string_width(state.message)
        if message_width > PANEL_WIDTH:
            logger.info("Message width: %d", message_width)
            scroll_duration = 0.9 * MSG_DURATION  # 90% of MSG_DURATION
            logger.info("Scroll duration: %f", scroll_duration)
            state.scroll_interval = scroll_duration / (message_width - PANEL_WIDTH)
            logger.info("Scroll interval: %f", state.scroll_interval)
        else:
            state.scroll_interval = 0
    elif msg.topic == TOPIC_POWER_SET:
        if msg.payload in (b"ON", b"OFF"):
            state.powered: bool = msg.payload == b"ON"
            logger.info("Power set to %s", state.powered)
            with hlock:
                # Turn on/off all panels
                # pylint: disable=no-value-for-parameter
                panels[0].set_relay(state.powered)
            client.publish(TOPIC_POWER, msg.payload)
        else:
            logger.warning("Invalid payload received for power state: %s", msg.payload)

    elif msg.topic == TOPIC_INVERT_SET:
        if msg.payload in (b"ON", b"OFF"):
            state.inverted = msg.payload == b"ON"
            logger.info("Invert set to %s", state.inverted)
            client.publish(TOPIC_INVERT, msg.payload)
        else:
            logger.warning("Invalid payload received for invert state: %s", msg.payload)


def mqtt_thread():
    """Thread for connecting to the MQTT broker."""
    host = os.environ.get("MQTT_BROKER", "mqttbroker.lan")
    user = os.environ.get("MQTT_USER")
    password = os.environ.get("MQTT_PASS")

    if DEBUG:
        host = "localhost"
    client = mqtt.Client()
    client.enable_logger(logger=logger)
    client.on_connect = on_mqtt_connect
    client.on_message = on_mqtt_message
    if user:
        logger.info("Logging into MQTT as %s", user)
        client.username_pw_set(user, password)
    client.connect(host, 1883, 60)
    client.loop_start()
    while state.running:
        time.sleep(1)
    client.publish(TOPIC_POWER, b"OFF", qos=0)
    client.publish(TOPIC_AVAILABILITY, "offline")
    client.loop_stop()
    client.disconnect()


def panel_thread():
    """Thread for updating the LED panel."""
    while state.running:
        if state.powered:
            if state.msg_until is not None:
                if base_font.string_width(state.message) > PANEL_WIDTH:
                    new_bitmap = render_text_bitmap(
                        state.message, int(-state.msg_offset)
                    )
                    state.msg_offset = (
                        state.msg_offset + state.scroll_interval
                    ) % base_font.string_width(state.message)
                else:
                    bitmap = render_text_bitmap(state.message, 0)
                if time.time() > state.msg_until:
                    state.msg_until = None
                    logger.info("Message expired")
            else:
                # Render the time if no message is active
                new_bitmap = render_time_bitmap()
            # Invert the bitmap if the inversion state is true
            if state.inverted:
                new_bitmap = bytearray(~b & 0xFF for b in new_bitmap)
            # Update the panel only if the bitmap has changed
            if state.bitmap != new_bitmap:
                with hlock:
                    for panel in panels:
                        # pylint: disable=no-value-for-parameter
                        panel.set_compiled_image(state.bitmap)
                state.bitmap = new_bitmap
            # Sleep for a while
            time.sleep(0.01)
        else:
            # If the panel is off, sleep for a longer while
            time.sleep(0.2)

    # Turn off the panel
    # pylint: disable=no-value-for-parameter
    panels[0].set_relay(False)

    shutdown_panel()


if __name__ == "__main__":
    logging.info("NAME %s", __name__)

    # Check if we are running in debug mode. Run as "python3 service.py debug"
    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        DEBUG = True

    if not init_panel(DEBUG):
        print("Could not find all three panels; aborting.")
        sys.exit(0)

    # Turn on the panel
    # pylint: disable=no-value-for-parameter
    panels[0].set_relay(True)

    # Set up signal handlers to gracefully shut down the service
    def signal_handler(mysignal, frame):
        # pylint: disable=unused-argument
        """Handle signals gracefully by stopping the main loop."""
        signal_name = signal.Signals(mysignal).name
        print(f"Caught {signal_name}; shutting down.")
        state.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start the threads to handle the MQTT connection and the panel
    mqtt_thread_instance = threading.Thread(target=mqtt_thread)
    panel_thread_instance = threading.Thread(target=panel_thread)
    panel_thread_instance.start()
    mqtt_thread_instance.start()
    panel_thread_instance.join()
