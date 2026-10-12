import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

CSV_HEADER = "Timestamp,T0,T1,T2,T3,HTR\n"


class CSVRotatingFileHandler(TimedRotatingFileHandler):

    def _write_header(self):
        if self.stream is None:
            self.stream = self._open()

        if Path(self.baseFilename).stat().st_size == 0:
            self.stream.write(CSV_HEADER)
            self.stream.flush()

    def doRollover(self):
        super().doRollover()
        self._write_header()


logger = logging.getLogger("warmer")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    log_path = Path(__file__).resolve().parent / "warmer.csv"

    file_handler = CSVRotatingFileHandler(
        filename=log_path,
        when="H",
        interval=12,
        backupCount=2,
        encoding="utf-8"
    )

    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s,%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    )

    logger.addHandler(file_handler)

    # Write header when the initial file is created
    file_handler._write_header()
