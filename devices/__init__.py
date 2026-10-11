from .display import Display
from .base import PWMBase, ADSBase

class Heater(PWMBase):
    pass

class Fan(PWMBase):
    pass

class Thermister(ADSBase):
    pass
