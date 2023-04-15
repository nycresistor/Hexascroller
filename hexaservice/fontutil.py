#!/usr/bin/env python3

import logging
from typing import Tuple, Dict
from PIL import Image, ImageChops

RED_MARKER = (255, 0, 0)
CHAR_HEIGHT = 7

logger = logging.getLogger(__name__)


def get_char(img: Image.Image, x: int) -> Tuple[Image.Image, int]:
    """
    Extract the character starting at x in img.
    Returns a tuple (image, next x after the marker).
    Uses a pixel of value RED_MARKER as the marker.
    """
    next_x = x
    while img.getpixel((next_x, 0)) != RED_MARKER:
        next_x += 1
    char_img = img.crop((x, 0, next_x, CHAR_HEIGHT))
    return (char_img, next_x + 1)


class Font:
    """
    Font class that represents a bitmap font with methods
    to calculate string widths and generate string images.
    """

    def __init__(self, path: str, inventory: str):
        x = 0
        self.fontmap: Dict[str, Image.Image] = {}
        try:
            self.base_img = Image.open(path)
        except FileNotFoundError:
            logger.error(f"Font file not found: {path}")
            raise
        for c in inventory:
            (char_img, x) = get_char(self.base_img, x)
            self.fontmap[c] = ImageChops.invert(char_img)

    def string_width(self, chars: str) -> int:
        # width of the characters plus one pixel between each character
        width = sum(self.fontmap[c].size[0] if c in self.fontmap else 2 for c in chars)
        width += len(chars) - 1
        return width

    def string_image(self, chars: str) -> Image.Image:
        img = Image.new("1", (self.string_width(chars), CHAR_HEIGHT))
        x = 0
        for c in chars:
            if c in self.fontmap:
                img.paste(self.fontmap[c], (x, 0))
                x += self.fontmap[c].size[0]
            else:
                # if the character is not in the fontmap, use a space
                x += 2
            # add a pixel between each character
            x += 1
        return img


base_font = Font(
    "basic-font.png",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.!?@/:;()#abcdefghijklmnopqrstuvwxyz,=^|-_+'\"",
)

if __name__ == "__main__":
    base_font.string_image("hello world").show()