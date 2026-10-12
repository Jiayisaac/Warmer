
import time
import math
from collections import deque


class PID:
    def __init__(
        self,
        kp: float = 0.15,
        ki: float = 0.002,
        kd: float = 0.5,
        kaw: float = 0.02,
        setpoint: int | float = 25.0,
        output_limits: tuple[int | float, int | float] = (0.0, 1.0),
        sample_time: int | float = 10.0,
        regression_window: float = 120.0,
    ):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.kaw = kaw
        self.setpoint = setpoint

        self.min_output, self.max_output = output_limits
        self.sample_time = sample_time
        self.regression_window = regression_window

        self.integral = 0.0
        self.output = 0.0
        self.last_update = None

        self.history = deque()

        # Diagnostic values
        self.p = 0.0
        self.i = 0.0
        self.d = 0.0
        self.rate = 0.0

    def reset(self):
        self.integral = 0.0
        self.output = 0.0
        self.last_update = None
        self.history.clear()

        self.p = self.i = self.d = 0.0
        self.rate = 0.0

    def add_sample(self, temperature, now=None):
        """Record temperature and remove old samples."""
        now = time.monotonic() if now is None else now

        if not math.isfinite(temperature):
            raise ValueError("Invalid temperature")

        self.history.append((now, temperature))

        cutoff = now - self.regression_window

        while self.history and self.history[0][0] < cutoff:
            self.history.popleft()

    def linear_regression(self):
        """Estimate temperature slope in °C/second."""
        if len(self.history) < 2:
            return 0.0

        t0 = self.history[0][0]
        x = [t - t0 for t, _ in self.history]
        y = [temp for _, temp in self.history]

        x_mean = sum(x) / len(x)
        y_mean = sum(y) / len(y)

        numerator = sum(
            (xi - x_mean) * (yi - y_mean)
            for xi, yi in zip(x, y)
        )

        denominator = sum(
            (xi - x_mean) ** 2 for xi in x
        )

        return (
            numerator / denominator
            if denominator > 0 else 0.0
        )

    def proportional(self, error):
        """Current temperature error."""
        return self.kp * error

    def derivative(self):
        """Derivative on measurement to avoid setpoint kick."""
        self.rate = self.linear_regression()
        return -self.kd * self.rate

    def integral_term(self, error, dt, p, d, lower, upper):
        """Integral back-calculation and anti-windup."""
        raw = p + self.integral + d
        actual = self.clamp(raw, lower, upper)
        tracking = min(self.kaw * dt, 1.0) * (actual - raw)
        self.integral = max(
            0.0,
            self.integral + self.ki * error * dt + tracking
        )
        return self.integral

    def clamp(self, value, lower, upper):
        return max(lower, min(upper, value))

    def output_limit(self, max_output=None):
        """Resolve dynamic heater power limit."""
        if max_output is None:
            return self.max_output

        return self.clamp(
            max_output,
            self.min_output,
            self.max_output
        )

    def update(self, temperature, max_output=None, now=None):
        """Calculate PID output when sample interval expires."""
        now = time.monotonic() if now is None else now

        if not math.isfinite(temperature):
            raise ValueError("Invalid temperature")
        upper = self.output_limit(max_output)
        lower = self.min_output
        self.add_sample(temperature, now)
        self.output = self.clamp(self.output, lower, upper)

        if self.last_update is None:
            dt = 0.0
        else:
            dt = now - self.last_update

            if dt < self.sample_time:
                return self.output

        error = self.setpoint - temperature

        self.p = self.proportional(error)
        self.d = self.derivative()
        self.i = self.integral_term(
            error, dt, self.p, self.d, lower, upper
        )

        raw_output = self.p + self.i + self.d
        self.output = self.clamp(raw_output, lower, upper)

        self.last_update = now
        return self.output
