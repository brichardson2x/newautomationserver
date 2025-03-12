from fastapi import Depends, HTTPException, Header
from app.core.config import settings
from app.core.logging import setup_logging

logger = setup_logging()

async def read_security(api_key: str = Header(None)):
    logger.debug("Checking API Key")

    if api_key is None:
        logger.error("API Key is missing")
        raise HTTPException(status_code=403, detail="API Key is missing")
    
    if api_key != settings.API_SECRET_KEY:
        logger.error("Invalid API Key")
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    logger.debug("API Key is valid")
    return {"message": "Access granted"}
    

#async def get_settings():
    #return settings