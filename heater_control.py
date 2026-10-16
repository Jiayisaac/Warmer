"""PID and heater-temperature safety calculations."""
import time
from pid import PID
from environment import ENVIRONMENT

class HeaterControl:
    def __init__(self, alert):
        self.alert = alert
        self.pid = PID(kp=ENVIRONMENT.KP, ki=ENVIRONMENT.KI,
                       kd=ENVIRONMENT.KD, kaw=ENVIRONMENT.KAW,
                       setpoint=ENVIRONMENT.SETPOINT,
                       sample_time=ENVIRONMENT.PID_UPDATE_TIME_SECS,
                       regression_window=ENVIRONMENT.PID_REGRESSION_SECS)
        self.disabled_until = time.monotonic()

    def reset(self):
        self.pid.reset()

    def power(self, heater_temp, chamber_temp):
        now = time.monotonic()
        if heater_temp >= ENVIRONMENT.MAX_HEATER_TEMP:
            self.disabled_until = now + ENVIRONMENT.OVERHEAT_DISABLE_MINS * 60
            self.alert.write(self.alert.HEATER_OVERTEMP)
            self.pid.reset()
            return 0.0
        if now < self.disabled_until:
            self.pid.reset()
            return 0.0
        if heater_temp <= ENVIRONMENT.MAX_HEATER_TEMP - 10:
            self.alert.clear(self.alert.HEATER_OVERTEMP)
            self.alert.clear(self.alert.HEATER_LIMITED)
            limit = 1.0
        else:
            self.alert.write(self.alert.HEATER_LIMITED)
            limit = max(0.0, min(1.0, (ENVIRONMENT.MAX_HEATER_TEMP - heater_temp) / 10.0))
        return min(self.pid.update(chamber_temp, max_output=limit), limit)
