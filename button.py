"""GPIO callbacks only enqueue events; no hardware output changes here."""
import time
from queue import SimpleQueue
from gpiozero import Button

class ButtonHandler:
    def __init__(self, pin, wake, hold_seconds=2.0):
        self.events = SimpleQueue()
        self.wake = wake
        self.started = None
        self.held = False
        self.button = Button(pin, pull_up=True, bounce_time=0.08,
                             hold_time=hold_seconds, hold_repeat=False)
        self.button.when_pressed = self._pressed
        self.button.when_held = self._held
        self.button.when_released = self._released
        self.hold_seconds = hold_seconds

    def _emit(self, event):
        self.events.put(event)
        self.wake.set()

    def _pressed(self):
        self.started = time.monotonic()
        self.held = False

    def _held(self):
        if self.started is not None and not self.held:
            self.held = True
            self._emit('TOGGLE_LED')

    def _released(self):
        if self.started is None:
            return
        duration = time.monotonic() - self.started
        self.started = None
        if duration >= self.hold_seconds:
            if not self.held:
                self.held = True
                self._emit('TOGGLE_LED')
        elif not self.held:
            self._emit('TOGGLE_WARMER')

    def close(self):
        self.button.when_pressed = None
        self.button.when_held = None
        self.button.when_released = None
        self.button.close()
