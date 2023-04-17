#!/usr/bin/env python3
import os
import socket
from typing import List
from led_panel import CommandCode, PANEL_HEIGHT, PANEL_WIDTH

UDP_IP = "0.0.0.0"
UDP_PORT = 9990
ID = 0

RELAY_ON = 1
RELAY_OFF = 0


def display_text(x: int, y: int, text: str):
    """Display text at the specified coordinates."""
    print(f"Display text ({x}, {y}): {text}")


def display_ascii_art(bitmap: List[List[int]]):
    """Display the bitmap as ASCII art."""
    os.system("clear")
    print(
        "".join([f"{i}                   " for i in range(6)])
        + " | "
        + "".join([f"{i}                   " for i in range(6, 12)]).replace(
            "10 ", "10"
        )
    )
    print("0 1 2 3 4 5 6 7 8 9 " * 6 + " | " + "0 1 2 3 4 5 6 7 8 9 " * 6)
    for row in bitmap:
        line = []
        for i, pixel in enumerate(row):
            if i == 60:
                line.append(" | ")
            if pixel:
                line.append("🔴")  # Red circle
            else:
                line.append("⚫")  # Black circle
        print("".join(line))
    print(" ")


def set_id(new_id: int):
    """Set the panel ID."""
    global ID
    ID = new_id
    print(f"Set ID: {ID}")


def query_id():
    """Query the panel ID."""
    global ID
    print(f"Query ID: {ID}")
    sock.sendto(bytes([ID]), addr)


def write_to_uart(data: bytes):
    """Write data to the UART."""
    print(f"Write to UART: {data}")


def set_relay(value: int):
    """Set the relay value."""
    print(f"Set relay: {'ON' if value == RELAY_ON else 'OFF'}")


def process_command(data: bytes):
    """Process the received command."""
    if len(data) < 1:
        print("No data received.")
        return

    command_code, payload_length = data[0], data[1]
    if len(data) != payload_length + 2:
        print(
            f"Error: Received data length ({len(data)}) does not match expected length ({payload_length + 2})"
        )
        return
    payload = data[2 : 2 + payload_length]

    if command_code == CommandCode.TEXT.value:
        x, y = payload[0], payload[1]
        text = payload[2:].decode("utf-8")
        display_text(x, y, text)

    elif command_code == CommandCode.BITMAP.value:
        bitmap = [[] for _ in range(PANEL_HEIGHT)]
        for i, byte in enumerate(payload):
            for j in range(PANEL_HEIGHT):
                bit = (byte >> (PANEL_HEIGHT - j)) & 1
                bitmap[j].append(bit)

        display_ascii_art(bitmap)

    elif command_code == CommandCode.SET_ID.value:
        set_id(payload)

    elif command_code == CommandCode.QUERY_ID.value:
        query_id()

    elif command_code == CommandCode.WRITE_UART.value:
        write_to_uart(payload)

    elif command_code == CommandCode.RELAY.value:
        set_relay(payload)

    else:
        print(f"Unknown command code: {command_code}, payload: {payload}")


def main():
    """Main function that initializes the socket and processes commands."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((UDP_IP, UDP_PORT))
        global addr
        while True:
            data, addr = sock.recvfrom(1024)
            process_command(data)


if __name__ == "__main__":
    main()
