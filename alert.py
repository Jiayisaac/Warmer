from collections import deque


class Alert:
    HEATER_OVERTEMP = "Heater Overtemp"
    HEATER_LIMITED = "Heater Limited"
    T0_PROBE_ERROR = "T0 Probe Error"
    T1_PROBE_ERROR = "T1 Probe Error"
    T2_PROBE_ERROR = "T2 Probe Error"
    T3_PROBE_ERROR = "T3 Probe Error"

    def __init__(self, max_alerts:int=6)->None:
        self._alerts = deque(maxlen=max_alerts)
        self._last_pos = -1

    def write(self, alert_text:str)->None:
        if alert_text not in self._alerts:
            self._alerts.append(alert_text)

    def read(self)->str:
        """Return the next alert, cycling through the queue."""
        if not self._alerts:
            return "Operation: Normal"

        self._last_pos = (
            self._last_pos + 1
        ) % len(self._alerts)

        return self._alerts[self._last_pos]

    def clear(self, alert_text: str) -> None:
        if alert_text in self._alerts:
            idx = self._alerts.index(alert_text)
            self._alerts.remove(alert_text)

            if idx <= self._last_pos:
                self._last_pos -= 1

            if not self._alerts:
                self._last_pos = -1

    def reset(self)->None:
        self._alerts.clear()
        self._last_pos = -1
