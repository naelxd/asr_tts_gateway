import logging
import sys
import json
import os


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def get_logger(name: str = "app") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(level)

    info_handler = logging.StreamHandler(sys.stdout)
    info_handler.setLevel(logging.INFO)
    info_handler.addFilter(lambda record: record.levelno < logging.ERROR)
    info_handler.setFormatter(JsonFormatter())

    error_handler = logging.StreamHandler(sys.stderr)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JsonFormatter())

    logger.addHandler(info_handler)
    logger.addHandler(error_handler)

    return logger


logger = get_logger()
