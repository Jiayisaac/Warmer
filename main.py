import time
import threading
from datetime import datetime
import math
import traceback
import board
import gpiozero
from pid import PID
from alert import Alert
from environment import ENVIRONMENT
from wifi import WiFi
from devices import Heater, Fan, Display, Thermister, LED
from web.main import run_web_server
from log import logger, clear_log

alert = Alert()
warmer_active = False
button_pressed_at = None

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

def avg(thermisters: list[Thermister], 
        tolerance:float=ENVIRONMENT.TOLERANCE)->float:
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

def button_pressed()->None:
    global button_pressed_at
    button_pressed_at = time.monotonic()

def button_released(button: gpiozero.Button, led: LED)->None:
    global button_pressed_at
    held_time = time.monotonic() - button_pressed_at
    if held_time < button.hold_time:
        # short press
        toggle_system()
    else:
        # long press
        toggle_led(led)

def toggle_system()->None:
    global warmer_active
    warmer_active = not warmer_active

def toggle_led(led: LED)->None:
    if led.active is None or led.active is False:
        led.active = True
        led.on()
    elif led.active is True:
        led.active = False
        led.off()

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
    button = None
    led = None

    try:
        heater_disable_until = time.monotonic()
        old_text = None

        i2c = board.I2C()
        heater = Heater(ENVIRONMENT.HEATER_GPIO)
        fan = Fan(ENVIRONMENT.FAN_GPIO)
        led = LED()
        led.off()

        pid = PID(
                    kp=KP,
                    ki=KI,
                    kd=KD,
                    setpoint=SETPOINT,
                    sample_time=PID_UPDATE_TIME_SECS,
                    regression_window=PID_REGRESSION_SECS,
                    kaw=KAW
                )
        
        display = Display(i2c)
        button = gpiozero.Button(ENVIRONMENT.BUTTON_GPIO, pull_up=True)

        button.when_activated = button_pressed
        button.when_released = lambda: button_released(button, led)

        while True:
            # loop watching system on / off button

            while warmer_active:
                # loop when system is on / active

                old_text = None
                fan.set_output(1)
                thermisters = []
                for i in range(4):
                    thermisters.append(Thermister(i2c,i))
        
                while warmer_active:
                    # Loop watching sensor data and adjusting outputs
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
        
                        temperatures = [t.temp[0] for t in thermisters]
                        logger.info(
                            "%.2f,%.2f,%.2f,%.2f,%.3f",
                            *temperatures,
                            heater.value
                        )
        
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
                        return
            if old_text != ["SYSTEM OFF"]:
                fan.set_output(0)
                heater.set_output(0)
                pid.reset()
                clear_log()
                display.write(["SYSTEM OFF"])
                old_text = ["SYSTEM OFF"]
            time.sleep(1)

    except Exception as e:
        print(f"An unknown exception {e} occurred.")
        traceback.print_exc()
        raise

    finally:
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

if __name__=="__main__":
    start()
