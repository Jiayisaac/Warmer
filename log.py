
import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

logger = logging.getLogger("warmer")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    log_path = Path(__file__).resolve().parent / "warmer.csv"

    file_handler = TimedRotatingFileHandler(
        filename=log_path,
        when="H",
        interval=12,
        backupCount=2,
        encoding="utf-8"
    )

    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s,%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    if log_path.stat().st_size == 0:
        logger.info("T0,T1,T2,T3,HTR")
