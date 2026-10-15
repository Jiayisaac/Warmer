import time
import math
import board
import neopixel
from adafruit_ads1x15 import ADS1115, ads1x15, AnalogIn
from gpiozero import PWMOutputDevice
from environment import ENVIRONMENT


class PWMBase:
    def __init__(self, gpio_pin: str = "GPIO12"):
        if gpio_pin not in ["GPIO12", "GPIO13", "GPIO17"]:
            raise AttributeError("GPIO must be one of GPIO12, GPIO13 or GPIO17")
        self._pwm = PWMOutputDevice(gpio_pin)
        self._commenced = time.monotonic()

    @property
    def value(self):
        return self._pwm.value
        
    @property
    def elapsed(self):
        return time.monotonic() - self._commenced

    def set_output(self, value):
        if not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError("Value must be an integer or a floating point number between 0.0 and 1.0")
        self._pwm.value = value

    def cleanup(self):
        self._pwm.value = 0
        self._pwm.off()
        self._pwm.close()


class ADSBase:
    """10 kOhm B3950 thermistor attached to a shared ADS1115."""
    R_FIXED = 10000.0
    R_NOMINAL = 10000.0
    BETA = 3950.0
    VCC = 3.3
    T_NOMINAL = 298.15

    def __init__(self, ads: ADS1115, ads_input_pin: int = 0):
        if not isinstance(ads, ADS1115):
            raise TypeError("Pass a shared ADS1115 instance, not the I2C bus")
        if ads_input_pin not in range(4):
            raise ValueError("ADS input pin must be 0-3")
        self.ads = ads
        self._digital = AnalogIn(ads, getattr(ads1x15.Pin, f"A{ads_input_pin}"))
        self._last_reading = None
        self._commenced = time.monotonic()

    @property
    def voltage(self):
        return self._digital.voltage

    @property
    def value(self):
        return self._digital.value

    @property
    def temp(self):
        voltage = self._digital.voltage
        if not math.isfinite(voltage) or not 0 < voltage < self.VCC:
            raise ValueError(f"Invalid thermistor voltage: {voltage}")
        # Fixed resistor to ground, NTC to VCC.
        resistance = self.R_FIXED * (self.VCC - voltage) / voltage
        temperature = 1.0 / (
            1.0 / self.T_NOMINAL
            + math.log(resistance / self.R_NOMINAL) / self.BETA
        ) - 273.15
        self._last_reading = (temperature, time.monotonic())
        return self._last_reading

    @property
    def elapsed(self):
        return time.monotonic() - self._commenced


class LED:
    def __init__(self)->None:
        self.active = False
        gpio = ENVIRONMENT.LED_GPIO
        pin = gpio.replace('GP', 'D')
        self.neopixel = neopixel.NeoPixel(getattr(board, pin), ENVIRONMENT.LED_NUMBER)

    def on(self)->None:
        self.active = True
        self.neopixel.fill((255,255,255))

    def off(self)->None:
        self.active = False
        self.neopixel.fill((0,0,0))

    def set_colour(self, 
                   led_number:int|None=None, 
                   colour: tuple[int,int,int]=(255,255,255))->None:
        if not isinstance(colour, tuple) or len(colour) != 3 or any(not isinstance(c, int) or not 0 <= c <= 255 for c in colour):
            raise AttributeError('Colour must be a tuple in the range of 0 to 255')
        if led_number is None and colour == (0,0,0):
            self.active = False
        if led_number is not None:
            if not isinstance(led_number, int) or not 0 <= led_number < ENVIRONMENT.LED_NUMBER:
                raise ValueError("Invalid LED index")
            self.neopixel[led_number] = colour
        else:
            self.neopixel.fill(colour)
