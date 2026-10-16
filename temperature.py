"""ADS1115 sampling and chamber consensus."""
import math
import threading
import time
from queue import Empty, Queue
from adafruit_ads1x15 import ADS1115
from devices import Thermister
from environment import ENVIRONMENT


def average_chamber(temperatures, alert, tolerance=ENVIRONMENT.TOLERANCE):
    readings = {i: t for i, t in enumerate(temperatures, 1)
                if t is not None and math.isfinite(t) and -10 <= t <= 80}
    if len(readings) < 2:
        raise ValueError('Insufficient valid chamber temperature probes')
    pairs = [(a, b) for a in readings for b in readings
             if a < b and abs(readings[a] - readings[b]) <= tolerance]
    if not pairs:
        raise ValueError('Chamber temperature probes disagree')
    accepted = set(pairs[0]) if len(readings) == 3 and len(pairs) == 1 else set(readings)
    values = [readings[i] for i in accepted]
    if max(values) - min(values) > tolerance:
        raise ValueError('Chamber temperature probes disagree')
    for i in range(1, 4):
        fault = getattr(alert, f'T{i}_PROBE_ERROR')
        (alert.clear if i in accepted else alert.write)(fault)
    return sum(values) / len(values)


class TemperatureSampler:
    def __init__(self, i2c, bus_lock, wake, interval, stop_event):
        ads = ADS1115(i2c)
        ads.gain = 1
        self.thermistors = [Thermister(ads, i) for i in range(4)]
        self.lock, self.wake, self.stop_event = bus_lock, wake, stop_event
        self.interval = max(0.1, float(interval))
        self.results = Queue(maxsize=1)
        self.thread = threading.Thread(target=self._run, daemon=True, name='temperature-sampler')

    def start(self):
        self.thread.start()

    def _run(self):
        while not self.stop_event.is_set():
            try:
                readings = []
                with self.lock:
                    for thermistor in self.thermistors:
                        try:
                            temp, _ = thermistor.temp
                            readings.append(temp if math.isfinite(temp) else None)
                        except (ValueError, TypeError, OverflowError, OSError):
                            readings.append(None)
                result = (time.monotonic(), readings)
            except Exception as exc:
                result = (time.monotonic(), exc)
            try:
                self.results.get_nowait()
            except Empty:
                pass
            self.results.put_nowait(result)
            self.wake.set()
            self.stop_event.wait(self.interval)

    def latest(self):
        try:
            return self.results.get_nowait()
        except Empty:
            return None

    def join(self, timeout=2.0):
        self.thread.join(timeout)
        return not self.thread.is_alive()
