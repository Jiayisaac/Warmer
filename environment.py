"""Environment variable management for the Pumpkin project."""
import os

from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv('.env')


@dataclass
class Environment:
    """Dataclass to hold environment variables"""
    SETPOINT : float = float(os.getenv('SETPOINT', '25.0'))
    MAX_HEATER_TEMP : float = float(os.getenv('MAX_HEATER_TEMP', '65.0'))
    KP : float = float(os.getenv('KP', '0.15')) # Proportional gain
    KI : float = float(os.getenv('KI', '0.0002')) # Integral gain
    KD : float = float(os.getenv('KD', '0.5')) # Derivative gain
    KAW : float = float(os.getenv('KAW', '0.02')) # Back-calculation gain
    PID_UPDATE_TIME_SECS : float = float(os.getenv('PID_UPDATE_TIME_SECS', '10.0'))
    PID_REGRESSION_SECS : float = float(os.getenv('PID_REGRESSION_SECS', '120.0'))
    OVERHEAT_DISABLE_MINS : int = int(os.getenv('OVERHEAT_DISABLE_MINS', '10'))
    MAIN_UPDATE_TIME_SECS : int = int(os.getenv('MAIN_UPDATE_TIME_SECS', '1'))

ENVIRONMENT = Environment()
