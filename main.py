import time
import threading
from datetime import datetime
import math
import traceback
import board
from pid import PID
from alert import Alert
from environment import ENVIRONMENT
from wifi import WiFi
from devices import Heater, Fan, Display, Thermister
from web.main import run_web_server

alert = Alert()

SETPOINT : float = ENVIRONMENT.SETPOINT
MAX_HEATER_TEMP : float = ENVIRONMENT.MAX_HEATER_TEMP
KP : float = ENVIRONMENT.KP
KI : float = ENVIRONMENT.KI
KD : float = ENVIRONMENT.KD
KAW : float = ENVIRONMENT.KAW
PID_UPDATE_TIME_SECS : float = ENVIRONMENT.PID_UPDATE_TIME_SECS
PID_REGRESSION_SECS : float = ENVIRONMENT.PID_REGRESSION_SECS
OVERHEAT_DISABLE_MINS : int = ENVIRONMENT.OVERHEAT_DISABLE_MINS
MAIN_UPDATE_TIME_SECS : int = ENVIRONMENT.MAIN_UPDATE_TIME_SECS

def avg(thermisters: list[Thermister], tolerance:float=2.0)->None:
    """Average valid thermistors with consensus checking."""

    readings = {}

    for idx, thermister in enumerate(thermisters, start=1):
        probe_error = getattr(alert, f"T{idx}_PROBE_ERROR")

        try:
            temp, _ = thermister.temp

            if not math.isfinite(temp):
                raise ValueError("Non-finite temperature")

            if not -10 <= temp <= 80:
                raise ValueError("Temperature outside valid range")

            readings[idx] = temp

        except (ValueError, TypeError, OverflowError):
            alert.write(probe_error)

    if len(readings) < 2:
        raise ValueError("Insufficient valid temperature probes")

    pairs = [
        (a, b)
        for a in readings
        for b in readings
        if a < b
        and abs(readings[a] - readings[b]) <= tolerance
    ]

    if not pairs:
        raise ValueError("Temperature probes disagree")

    if len(readings) == 3 and len(pairs) == 1:
        accepted = set(pairs[0])
    else:
        accepted = set(readings)

    values = [readings[idx] for idx in accepted]

    if max(values) - min(values) > tolerance:
        raise ValueError("Temperature probes disagree")

    for idx in range(1, len(thermisters) + 1):
        probe_error = getattr(alert, f"T{idx}_PROBE_ERROR")

        if idx in accepted:
            alert.clear(probe_error)
        else:
            alert.write(probe_error)

    return sum(values) / len(values)


def heater_power_limit(heater_temp: float, heater_disabled_until: float) -> float:
    """Return maximum permitted heater PWM (0.0–1.0)."""
    if not math.isfinite(heater_temp):
        raise ValueError("Heater temperature probe fault")

    if heater_temp <= 55:
        if time.monotonic() >= heater_disabled_until:
            alert.clear(alert.HEATER_OVERTEMP)
        alert.clear(alert.HEATER_LIMITED)
        return 1.0
    
    if heater_temp >= 65:
        alert.write(alert.HEATER_OVERTEMP)
        return 0.0

    alert.write(alert.HEATER_LIMITED)
    return (65.0 - heater_temp) / 10.0

def start()->None:
    wifi_thread = threading.Thread(
        target=WiFi.service,
        daemon=True
    )
    wifi_thread.start()

    web_thread = threading.Thread(
        target=run_web_server,
        daemon=True
    )
    web_thread.start()

    heater = None
    fan = None
    display = None
    i2c = None

    try:
        heater_disable_until = time.monotonic()
        old_text = None

        i2c = board.I2C()
        heater = Heater("GPIO12")
        fan = Fan("GPIO17")
        fan.set_output(1)
        display = Display(i2c)
        thermisters = []
        for i in range(4):
            thermisters.append(Thermister(i2c,i))
        
        pid = PID(
            kp=KP,
            ki=KI,
            kd=KD,
            setpoint=SETPOINT,
            sample_time=PID_UPDATE_TIME_SECS,
            regression_window=PID_REGRESSION_SECS,
            kaw=KAW
        )

        while True:
            try:
                curr_t = avg(thermisters[1:])
                htr_temp, _ = thermisters[0].temp

                if not math.isfinite(htr_temp) or not -10 <= htr_temp <= 120:
                    raise ValueError("Invalid temperature")

                if htr_temp >= MAX_HEATER_TEMP:
                    heater.set_output(0)
                    pid.reset()
                    heater_disable_until = (
                        time.monotonic() + (OVERHEAT_DISABLE_MINS * 60)
                    )
                    alert.write(alert.HEATER_OVERTEMP)

                elif time.monotonic() < heater_disable_until:
                    heater.set_output(0)
                    pid.reset()

                else:
                    max_power = heater_power_limit(htr_temp, heater_disable_until)
                    duty_cycle = pid.update(
                        curr_t,
                        max_output=max_power
                    )
                    heater.set_output(min(duty_cycle, max_power))

                text = [
                    f'Temp: {curr_t:.1f}°C',
                    f'Fan: {fan.value * 100:.0f}%',
                    f'Heater: {heater.value * 100:.0f}%',
                    alert.read()
                ]

                print(datetime.now())
                for line in text:
                    print(line)

                if text != old_text:
                    display.write(text)
                    old_text = text

                time.sleep(MAIN_UPDATE_TIME_SECS)

            except KeyboardInterrupt:
                heater.set_output(0)
                fan.set_output(0)
                display.write("SYSTEM SHUTDOWN...")
                break

    except Exception as e:
        print(f"An unknown exception {e} occurred.")
        traceback.print_exc()

    finally:
        if heater is not None:
            heater.cleanup()
        if fan is not None:
            fan.cleanup()
        if display is not None:
            display.cleanup()
        if i2c is not None:
            i2c.deinit()

if __name__=="__main__":
    start()
