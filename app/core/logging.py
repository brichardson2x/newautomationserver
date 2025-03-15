import logging
from logging.handlers import RotatingFileHandler
from app.core.config import settings

LOG_LEVELS = {
    "NOTSET": logging.NOTSET,
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}


def setup_logging():
    
    logger = logging.getLogger("app")
    
    if not logger.hasHandlers():
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        log_file_handler = RotatingFileHandler("app.log", maxBytes=1024*1024, backupCount=3)
        log_file_handler.setFormatter(formatter)
        logger.addHandler(log_file_handler)

        logger.setLevel(LOG_LEVELS[settings.LOG_LEVEL])

    return logger
