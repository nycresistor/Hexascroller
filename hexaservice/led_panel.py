#!/usr/bin/python3

import serial
import struct
import functools
import glob
import time
import logging
from typing import List, Optional, Union
from PIL import Image

CC_TEXT = 0xA1
CC_BITMAP = 0xA2
CC_SET_ID = 0xA3
CC_GET_ID = 0xA4
CC_UART = 0xA5
CC_RELAY = 0xA6


def compile_image(img: Image, x: int = 0, y: int = 0) -> bytes:
    width = min(img.size[0] - x, 120)
    height = min(7, img.size[1] - y)

    bitmap = bytearray(
        (img.getpixel((i + x, j + y)) & 1) << (7 - j)
        for j in range(height)
        for i in range(width)
    )

    return bytes(bitmap)


class Panel:
    def __init__(self, debug: Union[bool, int] = False):
        self.serial_port = None

        if debug is not False:
            self.debug = True
            self.id = debug
        else:
            self.debug = False

    def open(self, port_name: str, baud: int = 9600) -> None:
        if self.debug:
            import socket

            logging.info(f"Opening UDP socket to localhost : {port_name}")
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.port = port_name
        else:
            self.serial_port = serial.Serial(port_name, baud, timeout=0.5)
            logger.info(f"Opening serial port {self.serial_port.portstr}")
            try:
                self.serial_port.open()
            except serial.serialutil.SerialException as se:
                logging.warning(f"Serial port autoopened, probably ok. {se}")
            except serial.SerialException as e:
                logging.error(
                    f"Could not open serial port {self.serial_port.portstr}: {e}"
                )

    def command(self, command: int, payload: bytes) -> bytes:
        l = len(payload)
        packet = struct.pack("BB", command, l)
        if l > 0:
            packet = packet + payload
        if self.debug:
            self.sock.sendto(packet, ("127.0.0.1", self.port))
            return b""
        self.serial_port.write(packet)
        rsp = self.serial_port.read(2)
        if len(rsp) < 2 or rsp[0] != 0:
            if len(rsp) == 2:
                epl = rsp[1]
                if epl > 0:
                    rsp = rsp + self.serial_port.read(epl)
            return b""
        l = rsp[1]
        rpay = self.serial_port.read(l)
        return rpay

    def close(self) -> None:
        if self.debug:
            return
        self.serial_port.close()

    def set_relay(self, on: bool) -> None:
        try:
            if on:
                self.command(CC_RELAY, struct.pack("B", 1))
                logging.info("Relay on" for panel {self.id})
            else:
                logging.info("Relay off for panel {self.id}")
                self.command(CC_RELAY, struct.pack("B", 0))
        except Exception as e:
            logging.error(f"Error setting relay state for panel {self.id}: {e}")
            raise e

    def set_message(self, message: str, x: int = 0, y: int = 0) -> None:
        message = message[:100]
        cmd = struct.pack("bb", x, y) + message.encode()
        self.command(CC_TEXT, cmd)

    def set_image(self, img: Image, x: int = 0, y: int = 0) -> None:
        self.command(CC_BITMAP, compile_image(img, x, y))

    def set_compiled_image(self, bitmap: bytes) -> None:
        self.command(CC_BITMAP, bitmap)

    def get_id(self) -> int:
        if self.debug:
            return self.id

        v = self.command(CC_GET_ID, b"")
        self.id = v[0]
        logging.info(f"ID'd panel {self.id}")
        return self.id


panels: List[Optional[Panel]] = [None] * 3


def init_panels(debug: bool = False) -> bool:
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
                logging.info(f"Opening candidate {candidate}")
                p.open(candidate)
                panels[p.get_id()] = p
                logging.info(f"{candidate} succeeded")
            except Exception:
                p.close()
                logging.warning(f"{candidate} failed")
        return functools.reduce(lambda a, b: a & (b is not None), panels, True)


def shutdown_panels() -> None:
    for p in panels:
        p.close()
