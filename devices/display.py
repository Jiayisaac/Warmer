import time
from PIL import Image, ImageDraw, ImageFont
from adafruit_ssd1306 import SSD1306_I2C as SSD1306


class Display:
    def __init__(self, i2c, width:int = 128, height:int = 64):
        self.oled = SSD1306(width, height, i2c)
        self.oled.fill(0)
        self.oled.show()
        self._commenced = time.monotonic()

    @property
    def elapsed(self):
        return time.monotonic() - self._commenced
    
    def clear(self):
        self.oled.fill(0)
        self.oled.show()

    def write(self, text : str | list = ""):
        self.clear()
        image = Image.new("1", (self.oled.width, self.oled.height))
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=14)
        if isinstance(text, str):
            lines = text.split("\n")
        else:
            lines = text
        for row, txt in enumerate(lines):
            draw.text((0,row*20), txt, font=font, fill=255)
        self.oled.image(image)
        self.oled.show()

    def cleanup(self):
        self.clear()
