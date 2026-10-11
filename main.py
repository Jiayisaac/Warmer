import time
from datetime import datetime
import board
from devices import Heater, Fan, Display, Thermister

SETPOINT = 25

def avg(thermisters:list):
    t_sum = 0
    for t in thermisters:
        temp, _ = t.temp()
        t_sum += temp
    return t_sum / len(thermisters)

def start():
    try:
        heater_disable_until = time.monotonic()
        commenced_at = time.monotonic()
        i2c = board.I2C()
        heater = Heater("GPIO12")
        fan = Fan("GPIO17")
        fan.set_output(1)
        display = Display(i2c)
        thermisters = []
        for i in range(4):
            thermisters.append(Thermister(i2c,i))
        
        while True:
            try:
                curr_t = avg(thermisters[1:])
                htr_temp, _ = thermisters[0].temp
                if htr_temp > 65:
                    heater.set_output(0)
                    heater_disable_until = time.monotonic() + (10 * 60)
                if curr_t >= SETPOINT:
                    heater.set_output(0)
                if curr_t < SETPOINT:
                    if time.monotonic() >= heater_disable_until:
                        heater.set_output(1)
                text = [
                    f'Temperature: {curr_t:<15.1f}°C',
                    f'Fan: {fan.value * 100:<15.0f}%',
                    f'Heater: {heater.value * 100:<15.0f}%'
                ]
                print(datetime.now())
                for line in text:
                    print(line)
                display.write(text)
                time.sleep(5)
            except KeyboardInterrupt:
                heater.set_output(0)
                fan.set_output(0)
                display.write("SYSTEM OFF")
                break

    except Exception as e:
        print("An unknown exception {e} occurred.")

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
