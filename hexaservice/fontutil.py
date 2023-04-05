#!/usr/bin/env python3
from typing import Dict, Tuple
from PIL import Image, ImageChops


def get_char(img: Image.Image, x: int) -> Tuple[Image.Image, int]:
    """
    Extract the character starting at x in img.

    Args:
        img (Image.Image): Image object containing characters
        x (int): Starting x coordinate of the character to extract

    Returns:
        Tuple[Image.Image, int]: A tuple containing the extracted character image and the next x coordinate after the marker.
    """
    next_x = x
    while img.getpixel((next_x, 0)) != (255, 0, 0):
        next_x = next_x + 1
    char_img = img.crop((x, 0, next_x, 7))
    return char_img, next_x + 1


class Font:
    def __init__(self, path: str, inventory: str) -> None:
        """
        Initialize the Font object with a font image and a string of characters.

        Args:
            path (str): Path to the font image file
            inventory (str): A string of characters included in the font image
        """
        self.fontmap: Dict[str, Image.Image] = {}
        self.baseimg: Image.Image = Image.open(path)
        x = 0
        for c in inventory:
            char_img, x = get_char(self.baseimg, x)
            self.fontmap[c] = ImageChops.invert(char_img)

    def str_width(self, chars: str) -> int:
        """
        Calculate the width of a string in pixels when rendered with the font.

        Args:
            chars (str): The string to calculate the width for

        Returns:
            int: The width of the string in pixels
        """
        w = 0
        for c in chars:
            try:
                w = w + self.fontmap[c].size[0]
            except KeyError:
                w = w + 2
        w = w + len(chars) - 1
        return w

    def str_img(self, chars: str) -> Image.Image:
        """
        Create an image of the input string using the font.

        Args:
            chars (str): The string to render as an image

        Returns:
            Image.Image: The rendered image of the input string
        """
        img = Image.new("1", (self.str_width(chars), 7))
        x = 0
        for c in chars:
            try:
                img.paste(self.fontmap[c], (x, 0))
                x = x + self.fontmap[c].size[0]
            except KeyError:
                x = x + 2
            x = x + 1
        return img


base_font = Font('basic-font.png', "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.!?@/:;()#abcdefghijklmnopqrstuvwxyz,=^|-_+'\"")

if __name__ == '__main__':
    base_font.str_img('hello world').show()