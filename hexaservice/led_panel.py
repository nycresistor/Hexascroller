#!/usr/bin/python3

import glob
import os
import serial
import sys
import struct
import time
import functools
import logging
from enum import Enum
from typing import Union, List, Tuple
from PIL import Image


# Constants
class CommandCode(Enum):
    TEXT = 0xA1
    BITMAP = 0xA2
    SET_ID = 0xA3
    GET_ID = 0xA4
    UART = 0xA5
    RELAY = 0xA6

PANEL_HEIGHT = 7
PANEL_WIDTH = 120

# Configuring logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def compile_image(img, x=0, y=0):
    bitmap = b""
    width = min(img.size[0] - x, PANEL_WIDTH)
    height = min(PANEL_HEIGHT, img.size[1] - y)

    for i in range(width):
        b = 0
        for j in range(height):  # vertical scanning? jerk
            if img.getpixel((i + x, j + y)):
                b |= 1 << (PANEL_HEIGHT - j)
        bitmap = bitmap + struct.pack("B", b)
    return bitmap


class Panel:
    def __init__(self, debug : bool = False) -> None:
        self.serial_port = None

        if debug is not False:
            self.debug = True
            self.id = debug
        else:
            self.debug = False

    def open(self, port_name: str, baud: int = 9600) -> None:
        if self.debug:
            import socket

            logger.info(f"Opening UDP socket to localhost : {port_name}")
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.port = port_name

        else:
            self.serial_port = serial.Serial(port_name, baud, timeout=0.5)
            try:
                self.serial_port.open()
            except serial.serialutil.SerialException as se:
                logger.warning(f"Serial port autoopened, probably ok. {se}")
            except serial.SerialException as e:
                logger.error(f"Could not open serial port {self.serial_port.portstr}: {e}")
                sys.exit(1)

    def command(self, command: CommandCode, payload: bytes, expected: int) -> bytes:
        payload_length = len(payload)
        packet = struct.pack("BB", command.value, payload_length)
        if payload_length > 0:
            packet = packet + payload
        if self.debug:
            self.sock.sendto(packet, ("127.0.0.1", self.port))
            return b""
        self.serial_port.write(packet)
        rsp = self.serial_port.read(2)
        if len(rsp) < 2 or rsp[0] != 0:
            # if len(rsp) == 2:
            #     epl = rsp[1]
            #     if epl > 0:
            #         rsp = rsp + self.serial_port.read(epl)
            # logger.error(f"Error on panel {self.id}, command {command.value}. Response: {rsp}")
            return b""
        payload_length = rsp[1]
        response_payload = self.serial_port.read(payload_length)
        return response_payload

    def close(self):
        if self.debug:
            return
        self.serial_port.close()

    def set_relay(self, on: bool) -> None:
        if on:
            self.command(CommandCode.RELAY, struct.pack("B", 1), 0)
            logger.info("Relay on")
        else:
            logger.info("Relay off")
            self.command(CommandCode.RELAY, struct.pack("B", 0), 0)

    def set_message(self, message: str, x: int = 0, y: int = 0) -> None:
        message = message[:100]
        cmd = struct.pack("bb", x, y) + message.encode()
        self.command(CommandCode.TEXT, cmd, 0)

    def set_image(self, img: Image.Image, x: int = 0, y: int = 0) -> None:
        self.command(CommandCode.BITMAP, compile_image(img, x, y), 0)

    def set_compiled_image(self, bitmap: bytes) -> None:
        self.command(CommandCode.BITMAP, bitmap, 0)

    def get_id(self) -> int:
        if self.debug:
            return self.id

        v = self.command(CommandCode.GET_ID, b"", 1)
        self.id = v[0]
        logger.info(f"ID'd panel {self.id}")
        return self.id


panels: List[Panel] = [Panel] * 3
import glob
import time


def init_panel(debug: bool = False) -> bool:
    if debug:
        for port_num in range(0, 3):
            port = 9990 + port_num
            p = Panel(port_num)
            p.open(port)
            panels[port_num] = p
            time.sleep(0.1)
        return True

    else:
        for candidate in glob.glob("/dev/ttyACM*"):
            p = Panel()
            try:
                logger.info(f"Opening candidate {candidate}")
                p.open(candidate)
                panels[p.get_id()] = p
                logger.info(f"{candidate} succeeded")
            except Exception:
                p.close()
                logger.info(f"{candidate} failed")
        return all(panel is not None for panel in panels)


def shutdown_panel():
    for p in panels:
        p.close()
