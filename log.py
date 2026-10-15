import logging
import os
import pwd
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

CSV_HEADER = "Timestamp,T0,T1,T2,T3,HTR\n"


class CSVRotatingFileHandler(TimedRotatingFileHandler):
    """Rotating CSV log, writable by pi even when the service runs as root."""

    def _open(self):
        stream = super()._open()
        try:
            if os.geteuid() == 0:
                account = pwd.getpwnam("pi")
                os.fchown(stream.fileno(), account.pw_uid, account.pw_gid)
                os.fchmod(stream.fileno(), 0o664)
        except Exception:
            stream.close()
            raise
        return stream

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
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter(fmt="%(asctime)s,%(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(file_handler)
    file_handler._write_header()


def clear_log():
    for handler in logger.handlers:
        if isinstance(handler, CSVRotatingFileHandler):
            handler.acquire()
            try:
                if handler.stream is not None:
                    handler.stream.close()
                    handler.stream = None
                # Truncate using the handler's own open method so root restores
                # pi:pi ownership and group-write permissions if needed.
                with open(handler.baseFilename, "w", encoding="utf-8") as stream:
                    stream.write(CSV_HEADER)
                handler.stream = handler._open()
            finally:
                handler.release()
