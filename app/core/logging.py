import logging
from logging.handlers import RotatingFileHandler
import os
from app.core.config import settings

LOG_LEVEL = os.getenv('LOG_LEVEL', settings.LOG_LEVEL)

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

        logger.setLevel(LOG_LEVEL)

    return logger
