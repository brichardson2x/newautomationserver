from fastapi import Depends, FastAPI, HTTPException, Header
from app.core.config import settings
from app.core.logging import setup_logging
from app.dependencies import read_security, get_settings
from app.api.v1.endpoints import router as api_router

logger = setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="MS Graph API Automation"
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=["Root"])
async def root():
    logger.debug("Entered root endpoint")
    return {"message": "Welcome to the Salon Management API"}

