import logging
import sys
import threading
from logging.handlers import RotatingFileHandler

from constants import CACHE_DIR

LOG_FILE = CACHE_DIR / "voicemail_manager.log"


def setup_logging():
    logger = logging.getLogger()
    if getattr(setup_logging, "_configured", False):
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.propagate = False

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.getLogger("crash").exception(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    def handle_thread_exception(args):
        logging.getLogger("crash").exception(
            "Unhandled thread exception",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback)
        )

    sys.excepthook = handle_exception
    threading.excepthook = handle_thread_exception
    setup_logging._configured = True

    logger.info("============================================================")
    logger.info("Logging started. Log file: %s", LOG_FILE)
    return logger


def get_logger(name):
    setup_logging()
    return logging.getLogger(name)
