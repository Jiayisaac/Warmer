import math
import threading
import time
import traceback

import board
import gpiozero

from alert import Alert
from devices import Display, Fan, Heater, LED, Thermister
from adafruit_ads1x15 import ADS1115
from environment import ENVIRONMENT
from log import clear_log, logger
from pid import PID
from web.main import run_web_server
from wifi import WiFi


alert = Alert()


def average_chamber(temperatures, tolerance=ENVIRONMENT.TOLERANCE):
    """Consensus average of T1-T3; None denotes a failed measurement."""
    readings = {}
    for index, temp in enumerate(temperatures, start=1):
        if temp is not None and math.isfinite(temp) and -10 <= temp <= 80:
            readings[index] = temp

    if len(readings) < 2:
        raise ValueError("Insufficient valid chamber temperature probes")

    pairs = [
        (a, b) for a in readings for b in readings
        if a < b and abs(readings[a] - readings[b]) <= tolerance
    ]
    if not pairs:
        raise ValueError("Chamber temperature probes disagree")

    if len(readings) == 3 and len(pairs) == 1:
        accepted = set(pairs[0])
    else:
        accepted = set(readings)

    values = [readings[i] for i in accepted]
    if max(values) - min(values) > tolerance:
        raise ValueError("Chamber temperature probes disagree")

    for index in range(1, 4):
        fault = getattr(alert, f"T{index}_PROBE_ERROR")
        if index in accepted:
            alert.clear(fault)
        else:
            alert.write(fault)

    return sum(values) / len(values)


def read_temperatures(thermistors):
    """One read per ADS channel, with failed channels represented as None."""
    readings = []
    for index, thermistor in enumerate(thermistors):
        try:
            temperature, _ = thermistor.temp
            if not math.isfinite(temperature):
                raise ValueError("Non-finite temperature")
            readings.append(temperature)
        except (ValueError, TypeError, OverflowError, OSError) as exc:
            readings.append(None)
            print(f"T{index} read failed: {exc}")
    return readings


def heater_power_limit(heater_temp):
    """Linear derating over the last 10 degrees below MAX_HEATER_TEMP."""
    if heater_temp <= ENVIRONMENT.MAX_HEATER_TEMP - 10:
        alert.clear(alert.HEATER_LIMITED)
        return 1.0
    alert.write(alert.HEATER_LIMITED)
    return max(0.0, min(1.0, (ENVIRONMENT.MAX_HEATER_TEMP - heater_temp) / 10.0))


def start():
    heater = fan = display = i2c = button = led = None
    state_lock = threading.Lock()
    state_changed = threading.Event()
    warmer_active = False
    pressed_at = None

    def button_pressed():
        nonlocal pressed_at
        pressed_at = time.monotonic()

    def button_released():
        nonlocal pressed_at, warmer_active
        if pressed_at is None:
            return
        duration = time.monotonic() - pressed_at
        pressed_at = None
        if duration >= button.hold_time:
            led.off() if led.active else led.on()
            return
        with state_lock:
            warmer_active = not warmer_active
            if not warmer_active:
                heater.set_output(0)
        state_changed.set()

    try:
        i2c = board.I2C()
        heater = Heater(ENVIRONMENT.HEATER_GPIO)
        heater.set_output(0)
        fan = Fan(ENVIRONMENT.FAN_GPIO)
        fan.set_output(0)
        led = LED()
        led.off()
        display = Display(i2c)
        ads = ADS1115(i2c)
        ads.gain = 1
        thermistors = [Thermister(ads, i) for i in range(4)]
        pid = PID(
            kp=ENVIRONMENT.KP,
            ki=ENVIRONMENT.KI,
            kd=ENVIRONMENT.KD,
            setpoint=ENVIRONMENT.SETPOINT,
            sample_time=ENVIRONMENT.PID_UPDATE_TIME_SECS,
            regression_window=ENVIRONMENT.PID_REGRESSION_SECS,
            kaw=ENVIRONMENT.KAW,
        )
        button = gpiozero.Button(ENVIRONMENT.BUTTON_GPIO, pull_up=True)
        button.when_pressed = button_pressed
        button.when_released = button_released

        threading.Thread(target=WiFi.service, daemon=True).start()
        threading.Thread(target=run_web_server, daemon=True).start()

        was_active = False
        old_text = None
        heater_disabled_until = time.monotonic()

        while True:
            with state_lock:
                active = warmer_active

            if active != was_active:
                if active:
                    pid.reset()
                    fan.set_output(1)
                    old_text = None
                else:
                    with state_lock:
                        heater.set_output(0)
                    fan.set_output(0)
                    pid.reset()
                    clear_log()
                    old_text = None
                was_active = active

            if not active:
                text = ["SYSTEM OFF"]
                if text != old_text:
                    display.write(text)
                    old_text = text
                state_changed.wait(timeout=0.2)
                state_changed.clear()
                continue

            temperatures = read_temperatures(thermistors)
            heater_temp = temperatures[0]
            try:
                if heater_temp is None or not -10 <= heater_temp <= 120:
                    alert.write(alert.T0_PROBE_ERROR)
                    raise ValueError("Invalid heater thermistor reading")
                alert.clear(alert.T0_PROBE_ERROR)

                chamber_temp = average_chamber(temperatures[1:])
                now = time.monotonic()
                if heater_temp >= ENVIRONMENT.MAX_HEATER_TEMP:
                    heater_disabled_until = now + ENVIRONMENT.OVERHEAT_DISABLE_MINS * 60
                    alert.write(alert.HEATER_OVERTEMP)
                    pid.reset()
                    power = 0.0
                elif now < heater_disabled_until:
                    pid.reset()
                    power = 0.0
                else:
                    if heater_temp <= ENVIRONMENT.MAX_HEATER_TEMP - 10:
                        alert.clear(alert.HEATER_OVERTEMP)
                    limit = heater_power_limit(heater_temp)
                    power = min(pid.update(chamber_temp, max_output=limit), limit)

                with state_lock:
                    heater.set_output(power if warmer_active else 0)

                # Preserve the six-column CSV format; no error messages go into this logger.
                logger.info(
                    "%.2f,%.2f,%.2f,%.2f,%.3f",
                    *[t if t is not None else float("nan") for t in temperatures],
                    heater.value,
                )
                text = [
                    f"Temp: {chamber_temp:.1f}°C",
                    f"Fan: {fan.value * 100:.0f}%",
                    f"Heater: {heater.value * 100:.0f}%",
                    alert.read(),
                ]
            except (ValueError, TypeError, OverflowError, OSError) as exc:
                with state_lock:
                    heater.set_output(0)
                pid.reset()
                print(f"Sensor/control error: {exc}")
                text = ["SENSOR FAULT", "Heater: OFF", alert.read()]

            if text != old_text:
                display.write(text)
                old_text = text

            state_changed.wait(timeout=ENVIRONMENT.MAIN_UPDATE_TIME_SECS)
            state_changed.clear()

    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
        raise
    finally:
        if button is not None:
            button.close()
        if heater is not None:
            heater.cleanup()
        if fan is not None:
            fan.cleanup()
        if display is not None:
            display.cleanup()
        if i2c is not None:
            i2c.deinit()
        if led is not None:
            led.off()


if __name__ == "__main__":
    start()
