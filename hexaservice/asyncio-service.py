import os
import asyncio
import time
import sys
import logging
from aiologger import Logger

from PIL import Image
import asyncio_mqtt as aiomqtt

import led_panel
from fontutil import base_font
from led_panel import compile_image, panels

DEBUG = False

scroll_duration = 30.0  # 30 seconds for the message to finish rendering
panel_width = 120

TOPIC_PREFIX = "hexascroller"
TOPIC_POWER = f"{TOPIC_PREFIX}/power"
TOPIC_POWER_SET = f"{TOPIC_POWER}/set"
TOPIC_MESSAGE = f"{TOPIC_PREFIX}/message"
AVAILABILITY_TOPIC = f"{TOPIC_PREFIX}/available"


def internet_time() -> float:
    # https://en.wikipedia.org/wiki/Internet_time
    # Beat = (     time  + 1 hour) % 1 day * 1000  / 1 day
    return (((time.time() + 3600) % 86400) * 1000) / 86400


def render_time_bitmap() -> bytes:
    """
    Render the current time and internet time (swatch beats) as a bitmap to display on the panel.

    Returns:
        bytes: The compiled image bitmap suitable for the panel.
    """
    global panel_width

    beats = internet_time()
    msg = time.strftime("%H:%M:%S")
    txtimg = base_font.str_img(msg)
    img = Image.new("1", (panel_width, 7))
    img.paste(txtimg, (15, 0))
    bmsg = f"{beats:06.2f}"
    txt2img = base_font.str_img(bmsg)
    img.paste(txt2img, (62, 0))
    img.paste(base_font.str_img(".beats"), (93, 0))
    bitmap = compile_image(img, 0, 0)
    return bitmap


def render_message_bitmap(msg: str, offset: int) -> bytes:
    """
    Render the given message as a bitmap to display on the panel, considering the specified horizontal offset.

    Args:
        msg (str): The message to render.
        offset (int): The horizontal offset to apply to the message.

    Returns:
        bytes: The compiled image bitmap suitable for the panel.
    """
    global panel_width
    txtimg = base_font.str_img(msg)
    img = Image.new("1", (panel_width, 7))
    img.paste(txtimg, (offset, 0))
    bitmap = compile_image(img, 0, 0)
    return bitmap


async def mqtt_thread(client: aiomqtt.Client, logger: Logger):
    """
    The main MQTT thread that handles incoming messages for power and display settings.

    Args:
        client (aiomqtt.Client): The MQTT client instance.
        logger (Logger): The logger instance.
    """
    global powered, message, msg_until, scroll_duration

    # Subscribe to relevant topics
    topics = [TOPIC_POWER_SET, TOPIC_MESSAGE]
    for topic in topics:
        logger.debug(f"Subscribing to topic: {topic}")
        await client.subscribe(topic, 0)
        logger.debug(f"Subscribed to topic: {topic}")

    async for msg in client.filtered_messages(topics):
        if msg.topic == TOPIC_POWER_SET:
            logger.debug(f"Received power set message: {msg.payload}")
            powered = msg.payload.decode() == "ON"
            panels[0].set_relay(powered)
            await client.publish(TOPIC_POWER, msg.payload)
        elif msg.topic == TOPIC_MESSAGE:
            logger.debug(f"Received message: {msg.payload}")
            message = msg.payload.decode()
            msg_until = time.time() + scroll_duration


async def panel_thread(client: aiomqtt.Client, logger: Logger, hlock: asyncio.Lock):
    """
    The main panel thread that handles the display of messages and time on the panel.

    Args:
        client (aiomqtt.Client): The MQTT client instance.
        logger (Logger): The logger instance.
    """
    global powered, message, msg_until, panel_width, panels

    # Initialize the relay state and send the initial state to the MQTT broker
    logger.debug("Initializing relay state...")
    panels[0].set_relay(True)
    powered = True
    logger.debug("Relay state initialized. Publishing power state...")
    await client.publish(TOPIC_POWER, "ON")

    while True:
        if powered:
            # If there is a message to display and it hasn't expired yet
            if msg_until and time.time() < msg_until:
                # Calculate the width of the message in pixels
                text_width = base_font.str_width(message)

                # If the text is too long, scroll it
                if text_width > panel_width:
                    progress = 1 - ((msg_until - time.time()) / scroll_duration)
                    offset = int(progress * (text_width - panel_width))
                    logger.debug(
                        f"Scrolling message: {message}, offset={offset}, progress={progress}, width={text_width}"
                    )
                    bitmap = render_message_bitmap(message, offset)
                # If the text fits within the panel width, display it without scrolling
                else:
                    bitmap = render_message_bitmap(message, 0)
            # If there is no message or it has expired, display the time
            else:
                msg_until = None
                message = None
                bitmap = render_time_bitmap()

            # Update the panel display with the new bitmap
            async with hlock:
                for j in range(len(panels)):
                    panels[j].set_compiled_image(bitmap)

            # Refresh the display at a 60ms interval
            await asyncio.sleep(0.06)
        # If not powered, pause for a longer duration
        else:
            await asyncio.sleep(0.25)


async def main():
    global logger

    await led_panel.init(DEBUG)
    await panels[0].setRelay(True)


    host = os.environ.get("MQTT_BROKER", "homeassistant.local")
    user = os.environ.get("MQTT_USER")
    pw = os.environ.get("MQTT_PASS")

    if DEBUG:
        host = "localhost"

    logger.info(f"Connecting to MQTT broker as {user} at {host}...")
    async with aiomqtt.Client(host, username=user, password=pw) as client:
        logger.info("Connected to MQTT broker. Publishing availability...")
        await client.publish(AVAILABILITY_TOPIC, "online")
        hlock = asyncio.Lock()
        logger.info("Starting panel and MQTT threads...")
        panel_task = asyncio.create_task(panel_thread(client, logger, hlock))
        mqtt_task = asyncio.create_task(mqtt_thread(client, logger))

    try:
        await asyncio.gather(panel_task, mqtt_task)
    finally:
        logger.info("Shutting down...")
        led_panel.shutdown_panels()
        panels[0].set_relay(False)
        await client.publish(AVAILABILITY_TOPIC, "offline")
        await client.publish(TOPIC_POWER, "OFF")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        DEBUG = True

    logger = Logger.with_default_handlers(name="hexaservice", level=logging.DEBUG)
    logger.info("Starting up...")
    # if not panel_status:
    #     raise IOError("Failed to initialize all three LED panels. Aborting.")
    # else:
    #     logger.info("Initialized all three LED panels.")

    asyncio.run(main())
