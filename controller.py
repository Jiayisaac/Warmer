"""Single owner of operating state and all GPIO output devices."""
import math
import threading
import time
from queue import Empty
import board
from alert import Alert
from devices import Display, Fan, Heater, LED
from environment import ENVIRONMENT
from log import clear_log, logger
from button import ButtonHandler
from temperature import TemperatureSampler, average_chamber
from heater_control import HeaterControl
from web.main import run_web_server
from wifi import WiFi

class WarmerController:
    def __init__(self):
        self.stop_event = threading.Event()
        self.wake = threading.Event()
        self.i2c_lock = threading.Lock()
        self.active = True
        self.alert = Alert()
        self.heater_control = HeaterControl(self.alert)
        self.i2c = self.heater = self.fan = self.led = self.display = None
        self.button = self.sampler = None
        self.last_sample = None
        self.last_processed = None
        self.old_text = None
        self.was_active = False
        self.stale_after = max(3.0, 3 * ENVIRONMENT.MAIN_UPDATE_TIME_SECS)

    def start(self):
        self.i2c = board.I2C()
        self.heater = Heater(ENVIRONMENT.HEATER_GPIO)
        self.heater.set_output(0)
        self.fan = Fan(ENVIRONMENT.FAN_GPIO)
        self.fan.set_output(0)
        self.led = LED()
        self.led.off()
        try:
            self.display = Display(self.i2c)
        except (OSError, ValueError) as exc:
            print(f'Display unavailable: {exc}')
        self.sampler = TemperatureSampler(self.i2c, self.i2c_lock, self.wake,
                                          ENVIRONMENT.MAIN_UPDATE_TIME_SECS, self.stop_event)
        self.button = ButtonHandler(ENVIRONMENT.BUTTON_GPIO, self.wake)
        self.sampler.start()
        threading.Thread(target=WiFi.service, daemon=True).start()
        threading.Thread(target=run_web_server, daemon=True).start()

    def stop(self):
        self.stop_event.set()
        self.wake.set()

    def _events(self):
        while True:
            try:
                event = self.button.events.get_nowait()
            except Empty:
                break
            if event == 'TOGGLE_WARMER':
                self.active = not self.active
                if not self.active:
                    self.heater.set_output(0)
            elif event == 'TOGGLE_LED':
                (self.led.off if self.led.active else self.led.on)()

    def _transition(self):
        if self.active == self.was_active:
            return
        self.heater_control.reset()
        if self.active:
            self.fan.set_output(1)
            self.last_sample = None  # fresh measurement required before heating
            self.last_processed = None
        else:
            self.heater.set_output(0)
            self.fan.set_output(0)
            clear_log()
        self.old_text = None
        self.was_active = self.active

    def _control(self):
        if not self.active:
            return ['SYSTEM OFF']
        if self.last_sample is None:
            self.heater.set_output(0)
            return ['WAITING FOR SENSORS', 'Heater: OFF']
        timestamp, readings = self.last_sample
        if time.monotonic() - timestamp > self.stale_after:
            self.heater.set_output(0)
            self.heater_control.reset()
            return ['SENSOR TIMEOUT', 'Heater: OFF']
        if isinstance(readings, Exception):
            self.heater.set_output(0)
            self.heater_control.reset()
            return ['SENSOR FAULT', 'Heater: OFF']
        if timestamp == self.last_processed:
            return None
        self.last_processed = timestamp
        try:
            heater_temp = readings[0]
            if heater_temp is None or not math.isfinite(heater_temp) or not -10 <= heater_temp <= 120:
                self.alert.write(self.alert.T0_PROBE_ERROR)
                raise ValueError('Invalid heater thermistor reading')
            self.alert.clear(self.alert.T0_PROBE_ERROR)
            chamber_temp = average_chamber(readings[1:], self.alert)
            power = self.heater_control.power(heater_temp, chamber_temp)
            self.heater.set_output(power)
            logger.info('%.2f,%.2f,%.2f,%.2f,%.3f',
                        *[t if t is not None else float('nan') for t in readings],
                        self.heater.value)
            return [f'Temp: {chamber_temp:.1f}°C',
                    f'Fan: {self.fan.value * 100:.0f}%',
                    f'Heater: {self.heater.value * 100:.0f}%', self.alert.read()]
        except (ValueError, TypeError, OverflowError, OSError) as exc:
            self.heater.set_output(0)
            self.heater_control.reset()
            print(f'Sensor/control error: {exc}')
            return ['SENSOR FAULT', 'Heater: OFF', self.alert.read()]

    def _display(self, text):
        if text is None or text == self.old_text:
            return
        if self.display is not None:
            with self.i2c_lock:
                self.display.write(text)
        self.old_text = text

    def run(self):
        while not self.stop_event.is_set():
            self._events()
            self._transition()
            sample = self.sampler.latest()
            if sample is not None:
                self.last_sample = sample
            self._display(self._control())
            self.wake.wait(0.05)
            self.wake.clear()

    def shutdown(self):
        self.stop()
        if self.button is not None:
            self.button.close()
        # Outputs off before waiting on sensor thread / I2C.
        for device in (self.heater, self.fan):
            if device is not None:
                device.set_output(0)
        if self.led is not None:
            self.led.off()
        sampler_stopped = self.sampler is None or self.sampler.join()
        if not sampler_stopped:
            print('Sampler still running; leaving I2C resources open')
        if sampler_stopped and self.display is not None:
            self.display.clear()
            self.display.cleanup()
        for device in (self.heater, self.fan):
            if device is not None:
                device.cleanup()
        if sampler_stopped and self.i2c is not None:
            self.i2c.deinit()
