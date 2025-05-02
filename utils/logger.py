import os
import time
import logging
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from typing import Dict, Optional, TypeAlias, cast
import colorlog
from config import BASE_DIR
from colorlog import ColoredFormatter

SUCCESS_LEVEL_NUM = 25
TRACE_LEVEL_NUM = 5

logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")
logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")


class CustomLogger(logging.Logger):
    def success(self, message, *args, **kws):
        if self.isEnabledFor(SUCCESS_LEVEL_NUM):
            self._log(SUCCESS_LEVEL_NUM, message, args, **kws)

    def trace(self, message, *args, **kws):
        if self.isEnabledFor(TRACE_LEVEL_NUM):
            self._log(TRACE_LEVEL_NUM, message, args, **kws)


logging.setLoggerClass(CustomLogger)
LoggerType: TypeAlias = CustomLogger


class UTCFormatter(logging.Formatter):
    converter = time.gmtime

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            t = dt.strftime("%Y-%m-%d %H:%M:%S")
            s = f"{t},{record.msecs:03d}"
        return s


class Logger:
    loggers: Dict[str, LoggerType] = {}

    @staticmethod
    def init(logger_name: str, save_to_file=False) -> LoggerType:
        logger_folder = ""

        if "/" in logger_name:
            logger_folder = logger_name.split("/")[0]
            logger_name = logger_name.split("/")[-1]

        logger = logging.getLogger(logger_name)
        logger.setLevel(TRACE_LEVEL_NUM)
        logger.propagate = False

        if not logger.hasHandlers():
            safe_file_name = logger_name.replace(" ", "_").replace(":", "_")
            safe_file_name = os.path.splitext(safe_file_name)[0]

            if logger_folder == "":
                log_dir = os.path.join(BASE_DIR, "logs", "general")
            else:
                log_dir = os.path.join(BASE_DIR, "logs", logger_folder)

            archive_dir = os.path.join(log_dir, "archive")
            if not os.path.exists(archive_dir):
                os.makedirs(archive_dir)

            log_path = os.path.join(log_dir, f"{safe_file_name}.log")

            if save_to_file:
                if not os.path.exists(os.path.dirname(log_dir)):
                    os.makedirs(os.path.dirname(log_dir))

                file_handler = TimedRotatingFileHandler(
                    log_path,
                    when="midnight",
                    interval=1,
                    backupCount=28,
                    encoding="utf-8",
                    delay=False,
                    utc=True,
                )
                file_handler.namer = lambda name: name.replace(log_dir, archive_dir)

                file_formatter = UTCFormatter(
                    "%(asctime)s | %(levelname)-8s | %(name)s | line: %(lineno)-5s | %(message)s",
                    "%Y-%m-%d %H:%M:%S",
                )
                file_handler.setFormatter(file_formatter)
                file_handler.setLevel(TRACE_LEVEL_NUM)
                logger.addHandler(file_handler)

            handler = colorlog.StreamHandler()
            formatter = ColoredFormatter(
                fmt="%(light_blue)s%(asctime)s%(reset)s | %(log_color)s%(levelname)-8s%(reset)s | %(blue)s%(name)-22s%(reset)s | line: %(purple)s%(lineno)s%(reset)s\\t | %(white)s%(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
                reset=True,
                secondary_log_colors={},
                style="%",
                log_colors={
                    "SUCCESS": "bold_green",
                    "TRACE": "bold_purple",
                    "INFO": "bold_cyan",
                    "DEBUG": "light_blue",
                    "WARNING": "bold_yellow",
                    "ERROR": "bold_red",
                    "CRITICAL": "bold_red",
                },
            )
            handler.setFormatter(formatter)
            handler.setLevel(TRACE_LEVEL_NUM)
            logger.addHandler(handler)

        Logger.loggers[logger_name] = logger
        custom_logger = cast(CustomLogger, logger)
        return custom_logger

    @staticmethod
    def get_logger(logger_name: str) -> Optional[LoggerType]:
        return Logger.loggers.get(logger_name)

    @staticmethod
    def close():
        for logger in Logger.loggers.values():
            handlers = list(logger.handlers)
            for handler in handlers:
                logger.removeHandler(handler)
                handler.close()
        Logger.loggers.clear()
