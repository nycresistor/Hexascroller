#!/usr/src/python3

from PIL import Image, ImageDraw, ImageChops


def getChar(img, x):
    """Extract the character starting at x in img.
    Returns a tuple (image, next x after the marker).
    Uses a pixel of value (255,0,0) as the marker."""
    nextx = x
    while img.getpixel((nextx, 0)) != (255, 0, 0):
        nextx = nextx + 1
    charimg = img.crop((x, 0, nextx, 7))
    return (charimg, nextx + 1)


class Font:
    def __init__(self, path, inventory):
        x = 0
        self.fontmap = {}
        self.baseimg = Image.open(path)
        for c in inventory:
            (charimg, x) = getChar(self.baseimg, x)
            self.fontmap[c] = ImageChops.invert(charimg)

    def strWidth(self, chars):
        w = 0
        for c in chars:
            try:
                w = w + self.fontmap[c].size[0]
            except KeyError:
                w = w + 2
        w = w + len(chars) - 1
        return w

    def strImg(self, chars):
        img = Image.new("1", (self.strWidth(chars), 7))
        # d = ImageDraw.Draw(img)
        # d.rectangle(((0,0),img.size),fill=255)
        x = 0
        for c in chars:
            try:
                img.paste(self.fontmap[c], (x, 0))
                x = x + self.fontmap[c].size[0]
            except KeyError:
                x = x + 2
            x = x + 1
        return img


base_font = Font(
    "basic-font.png",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.!?@/:;()#abcdefghijklmnopqrstuvwxyz,=^|-_+'\"",
)

if __name__ == "__main__":
    base_font.strImg("hello world").show()
