import time
import math
from adafruit_ads1x15 import ADS1115, ads1x15, AnalogIn
from gpiozero import PWMOutputDevice


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
    R_FIXED = 10000
    R_NOMINAL = 10000
    BETA = 3950
    VCC = 3.3
    T_NOMINAL = 298.15  # 25°C in Kelvin

    def __init__(self, i2c, ads_input_pin: int = 0):
        if ads_input_pin not in range(0,4):
            raise AttributeError("Input pin not in range 0-3")
        self.ads = ADS1115(i2c)
        self.ads.gain = 1
        self._digital = AnalogIn(self.ads, getattr(ads1x15.Pin, f"A{ads_input_pin}"))
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
        return self._read_temperature()
    
    @property
    def elapsed(self):
        return time.monotonic() - self._commenced
    
    def _read_temperature(self):
        voltage = self._digital.voltage
        resistance = self.R_FIXED * (self.VCC - voltage) / voltage
        temperature = 1 / (
                1 / self.T_NOMINAL +
                math.log(resistance / self.R_NOMINAL) / self.BETA
            ) - 273.15
        self._last_reading = (temperature, time.monotonic())
        return self._last_reading
