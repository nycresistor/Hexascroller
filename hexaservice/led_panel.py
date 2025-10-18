#!/usr/bin/python3

"""
This module contains functions and classes to control an LED panel.

It provides the following functionality:

1. Compile images into a byte sequence for the LED panel.
2. Initialize and shut down the LED panel.
3. Interact with the LED panel by sending commands and data (e.g., text and images).

The main components of this module are:

- CommandCode: An enumeration of command codes used to interact with the LED panel.
- compile_image: A function to compile an image into a byte sequence for the LED panel.
- init_panel: A function to initialize the LED panel.
- shutdown_panel: A function to shut down the LED panel.
- Panel: A class representing an LED panel. It provides methods to open/close a
  connection, send commands, and manipulate the content displayed on the panel
  (e.g. setting text, images, and relay states).

*Hexascroller* has three panels consisting of two 60x7 LED matrices.
Each panel is controlled by a separate Teensy board.
The Teensy boards are connected to a Raspberry Pi Zero W via USB, on a single USB hub.
The Raspberry Pi is connected to the Internet via Wi-Fi.
The Raspberry Pi is also connected to a 5V power supply via a micro USB cable.

"""

import glob
import socket
import struct
import sys
import logging
from enum import Enum
from typing import List, Optional
from PIL import Image
import serial


# Constants
class CommandCode(Enum):
    """
    An enumeration of command codes used to interact with the LED panel.

    There are more command codes defined in the Teensy code, but these are the only
    ones used by this module.
    """

    STATUS = 0xA0  # 160
    TEXT = 0xA1  # 161
    BITMAP = 0xA2  # 162
    SET_ID = 0xA3  # 163
    GET_ID = 0xA4  # 164
    WRITE_UART = 0xA5  # 165
    RELAY = 0xA6  # 166
    FLIP_BUFFERS = 0xB2
    BITMAP_BACK_HALF_ONE = 0xB3
    BITMAP_BACK_HALF_TWO = 0xB4


PANEL_HEIGHT = 7
PANEL_WIDTH = 120

# Configuring logging
logger = logging.getLogger(__name__)


def compile_image(img: Image.Image, x_pos: int = 0, y_pos: int = 0) -> bytes:
    """Compile the given image into a byte sequence for the LED panel.

    Args:
        img (Image.Image): The image to be compiled.
        x_pos (int, optional): The x-coordinate of the starting point. Defaults to 0.
        y_pos (int, optional): The y-coordinate of the starting point. Defaults to 0.

    Returns:
        bytes: The compiled bitmap sequence representing the image.
    """
    bitmap = b""
    width = min(img.size[0] - x_pos, PANEL_WIDTH)
    height = min(PANEL_HEIGHT, img.size[1] - y_pos)

    for column in range(width):
        raw_bitmap = 0
        for row in range(height):  # vertical scanning? jerk
            if img.getpixel((column + x_pos, row + y_pos)):
                raw_bitmap |= 1 << (PANEL_HEIGHT - row)
        bitmap = bitmap + struct.pack("B", raw_bitmap)
    return bitmap


def init_panel(debug_host: Optional[str] = None) -> bool:
    """Initialize the LED panel.

    Args:
        debug_host (str, optional): Host to send debug messages to. Defaults to None.

    Returns:
        bool: True if the panel is successfully initialized, False otherwise.
    """
    # pylint: disable=no-else-return
    logger.debug("Initializing panel")
    if debug_host:
        logger.debug("Debug host is %s", debug_host)
        logging.basicConfig(level=logging.DEBUG)
        panel = Panel(debug_host)
        panel.open("debug")
        panels[0] = panel
        del panels[2]
        del panels[1]
        return True
    else:
        for candidate in glob.glob("/dev/ttyACM*"):
            panel = Panel()
            try:
                logger.info("Opening candidate %s", candidate)
                panel.open(candidate)
                panels[panel.get_id()] = panel
                logger.info("Candidate %s succeeded", candidate)
            except Exception as exception:
                logger.info("Candidate %s failed, got %s", candidate, exception)
                panel.close()
        return all(panel is not None for panel in panels)


def shutdown_panel():
    """Shut down the LED panel. Closes the serial ports."""
    for panel in panels:
        panel.close()


class Panel:
    """
    A class representing an individual LED panel.

    It can be used to set the message on the panel, set the image on the panel, and turn the
    relay on or off. Hexascroller has 3 panels, so there are 3 instances of this class.
    """

    def __init__(self, debug_host: Optional[str] = None) -> None:
        """Initialize the Panel object."""
        self.debug_host = debug_host
        logger.info("Debug host is %s", debug_host)
        if debug_host:
            self.id = 0  # pylint: disable=invalid-name
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.port = 9990
        else:
            self.serial_port = serial.Serial()
            self.id = -1

    def open(self, port_name: str, baud: int = 57600) -> None:
        """Open a connection to the LED panel.

        Args:
            port_name (str): The port name to use for the connection.
            baud (int, optional): The baud rate for the serial connection.
                                  Defaults to 57600.
        """
        if port_name == "debug":
            logger.info(
                "Will use UDP socket to debug_host %s : %d", self.debug_host, self.port
            )

        else:
            self.serial_port = serial.Serial(port_name, baud, timeout=0.5)
            try:
                self.serial_port.open()
            except serial.serialutil.SerialException as serial_exception:
                logger.warning(
                    "Serial port autoopened, probably ok. %s", serial_exception
                )
            except serial.SerialException as serial_exception:
                logger.error(
                    "Could not open serial port %s: %s",
                    port_name,
                    serial_exception,
                )
                sys.exit(1)

    def command(self, command: CommandCode, payload: bytes, expected: int) -> bytes:
        """
        Send a command to the LED panel with the given payload and expect a response.

        :param command: The command code to be sent.
        :param payload: The payload data associated with the command.
        :param expected: The value expected in the response.
        :return: The response payload as bytes.
        """
        payload_length = len(payload)
        logger.debug(
            "Sending command %s, payload length %i", command.value, payload_length
        )
        packet = struct.pack("BB", command.value, payload_length)
        if payload_length > 0:
            packet = packet + payload
        logger.debug(
            "Sending UDP packet to %s: %s",
            self.debug_host,
            "".join("{:02x}".format(x) for x in packet),
        )
        if self.debug_host:
            self.sock.sendto(packet, (self.debug_host, self.port))
            return b""
        logger.debug(
            "Sending serial packet to %s: %s",
            self.serial_port.name,
            ("".join("{:02x}".format(x) for x in packet)),
        )
        self.serial_port.write(packet)
        self.serial_port.flush()
        rsp = self.serial_port.read(2)
        if len(rsp) < 2 or rsp[0] != 0:
            if len(rsp) == 2:
                epl = rsp[1]
                if epl > 0:
                    rsp = rsp + self.serial_port.read(epl)
            if rsp[0] != expected:
                logger.error(
                    "Error on panel %s, command %s. Expected %s but got response: %s",
                    self.id,
                    command.value,
                    expected,
                    rsp[0],
                )
            return b""
        payload_length = rsp[1]
        response_payload = self.serial_port.read(payload_length)
        return response_payload

    def close(self):
        """Close the connection to the LED panel."""
        if self.debug_host:
            return
        else:
            self.serial_port.close()

    # pylint: disable=invalid-name
    def set_relay(self, on: bool) -> None:
        """
        Set the relay state of the LED panel.

        :param on: A boolean value to indicate the relay state. True for on, False for off.
        """
        if on:
            self.command(CommandCode.RELAY, struct.pack("B", 1), 0)
            logger.info("Relay on panel %s on", self.id)
        else:
            logger.info("Relay on panel %s off", self.id)
            self.command(CommandCode.RELAY, struct.pack("B", 0), 0)

    def set_message(self, message: str, x_pos: int = 0, y_pos: int = 0) -> None:
        """
        Set a text message to be displayed on the LED panel, using the built-in font.

        :param message: The message to be displayed.
        :param x_pos: The horizontal position of the message on the panel (default: 0).
        :param y_pos: The vertical position of the message on the panel (default: 0).
        """
        if not isinstance(message, str):
            raise ValueError("Message must be a string.")
        if not 0 <= x_pos < PANEL_WIDTH or not 0 <= y_pos < PANEL_HEIGHT:
            raise ValueError(
                f"Invalid x, y coordinates. Must be within panel dimensions ({PANEL_WIDTH}, {PANEL_HEIGHT})."
            )

        message = message[:100]
        cmd = struct.pack("bb", x_pos, y_pos) + message.encode()
        self.command(CommandCode.TEXT, cmd, 0)

    def set_image(self, img: Image.Image, x_pos: int = 0, y_pos: int = 0) -> None:
        """
        Set an image to be displayed on the LED panel.

        :param img: The image to be displayed.
        :param x_pos: The horizontal position of the image on the panel (default: 0).
        :param y_pos: The vertical position of the image on the panel (default: 0).
        """
        if not isinstance(img, Image.Image):
            raise ValueError("Image must be a PIL.Image.Image object.")
        if not 0 <= x_pos < PANEL_WIDTH or not 0 <= y_pos < PANEL_HEIGHT:
            raise ValueError(
                f"Invalid x, y coordinates. Must be within panel dimensions ({PANEL_WIDTH}, {PANEL_HEIGHT})."
            )

        self.command(CommandCode.BITMAP, compile_image(img, x_pos, y_pos), 0)

    def set_compiled_image(self, bitmap: bytes) -> None:
        """
        Set a precompiled image bitmap to be displayed on the LED panel.

        :param bitmap: The precompiled image bitmap.
        """
        if not isinstance(bitmap, bytes):
            raise ValueError(
                f"Bitmap must be a bytes object. instead got: {type(bitmap)}"
            )
        if len(bitmap) != PANEL_WIDTH:
            raise ValueError(
                f"Bitmap length must be equal to number of panel width ({PANEL_WIDTH} bytes). Instead got {len(bitmap)} bytes."
            )

        self.command(CommandCode.BITMAP_BACK_HALF_ONE, bitmap[: PANEL_WIDTH // 2], 0)
        self.command(CommandCode.BITMAP_BACK_HALF_TWO, bitmap[PANEL_WIDTH // 2 :], 0)
        self.command(CommandCode.FLIP_BUFFERS, b"", 0)

    def get_id(self) -> int:
        """
        Get the ID of the LED panel.

        :return: The ID of the LED panel as an integer.
        """
        if self.debug_host:
            return 0

        id_value = self.command(CommandCode.GET_ID, b"", 1)
        self.id = int(id_value[0])
        logger.info("ID'd panel %d", self.id)
        return self.id


panels: List[Panel] = [Panel()] * 3
