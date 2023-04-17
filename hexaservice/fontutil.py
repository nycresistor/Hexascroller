#!/usr/bin/env python3

"""
`fontutil` is a Python module for working with custom bitmap fonts. The module provides
 a `Font` class that can be used to load a bitmap font image and its inventory of
 characters, calculate the width of a given string, and generate a single image
 representing the input string using the loaded font.

The bitmap font image should have the characters separated by a red marker (255, 0, 0)
at the top of each character. The height of each character should be consistent, and
the width can vary depending on the character.

The `Font` class constructor accepts two parameters:
- `path`: A string representing the path to the font image file.
- `inventory`: A string containing the characters included in the font image in the
   same order as they appear in the image.

The `Font` class provides two methods:
- `string_width(chars: str) -> int`: Accepts a string `chars` and returns the total
   width of the string using the loaded font.
- `string_image(chars: str) -> Image.Image`: Accepts a string `chars` and returns an
  `Image.Image` object representing the input string using the loaded font.

Example usage:

```python
from fontutil import Font

base_font = Font(
    "basic-font.png",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.!?@/:;()#abcdefghijklmnopqrstuvwxyz,=^|-_+'\"",
)

test_string = "Hello world!"
text_width = base_font.string_width(test_string)
print(f"Width of '{test_string}' is {text_width} pixels.")
text_image = base_font.string_image(test_string)
text_image.show()
"""

import logging
from typing import Tuple, Dict
from PIL import Image, ImageChops

RED_MARKER = (255, 0, 0)
CHAR_HEIGHT = 7

logger = logging.getLogger(__name__)


def get_char(img: Image.Image, x_pos: int) -> Tuple[Image.Image, int]:
    """
    Extract the character starting at x in img.
    Uses a pixel of value RED_MARKER as the limit marker.

    Args:
        img (Image.Image): Source image containing the character.
        x_pos (int): Starting x position of the character in the image.

    Returns:
        Tuple[Image.Image, int]: A tuple containing the extracted character image and
        the next x position after the marker.

    """
    next_x = x_pos
    logger.debug("Extracting character at x %d", x_pos)
    while img.getpixel((next_x, 0)) != RED_MARKER:
        next_x += 1
        logger.debug("Next x: %d", next_x)
    char_img = img.crop((x_pos, 0, next_x, CHAR_HEIGHT))
    return (char_img, next_x + 1)


class Font:
    """
    A class representing a bitmap font with methods to calculate string widths and
    generate images of strings.
    """

    def __init__(self, path: str, inventory: str):
        """
        Initialize a Font object.

        Args:
            path (str): Path to the font image file.
            inventory (str): String containing all characters supported by the font.
        """
        x_pos = 0
        self.fontmap: Dict[str, Image.Image] = {}
        try:
            self.base_img = Image.open(path)
        except FileNotFoundError:
            logger.error("Font file not found: %s", path)
            raise
        for char in inventory:
            logger.debug("Loading character: %s at x %d", char, x_pos)
            if x_pos >= self.base_img.size[0]:
                logger.error("Character not found in font image at position %i: '%s'", x_pos, char)
                continue
            (char_img, x_pos) = get_char(self.base_img, x_pos)
            self.fontmap[char] = ImageChops.invert(char_img)

    def string_width(self, chars: str) -> int:
        """
        Calculate the width of a string rendered in the font.

        Args:
            chars (str): The string to measure.

        Returns:
            int: The width of the rendered string in pixels.
        """
        width = sum(self.fontmap[c].size[0] if c in self.fontmap else 2 for c in chars)
        # plus one pixel between each character
        width += len(chars) - 1
        return width

    def string_image(self, chars: str) -> Image.Image:
        """
        Generate an image of a string rendered in the font.

        Args:
            chars (str): The string to render.

        Returns:
            Image.Image: The rendered string as an image.
        """
        img = Image.new("1", (self.string_width(chars), CHAR_HEIGHT))
        x_pos = 0
        for char in chars:
            if char in self.fontmap:
                img.paste(self.fontmap[char], (x_pos, 0))
                x_pos += self.fontmap[char].size[0]
            else:
                # if the character is not in the fontmap, use a space
                if char != " ": # don't log a warning for spaces
                    logger.warning("Character not found in font: %s", char)
                x_pos += 2
            # add a pixel between each character
            x_pos += 1
        return img


# Initialize the base_font instance
base_font = Font(
    "basic-font.png",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.!?@/:;()#abcdefghijklmnopqrstuvwxyz,=^|-_+'\"~",
)

if __name__ == "__main__":
    base_font.string_image("Hello world!").show()
