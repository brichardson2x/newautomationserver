from fastapi import FastAPI
import uvicorn
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.endpoints import router as api_router, add_middleware

logger = setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="MS Graph API Automation"
)

add_middleware(app)

app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.FASTAPI_HOST, port=settings.FASTAPI_PORT, reload=settings.FASTAPI_DEBUG)

@app.get("/", tags=["Root"])
async def root():
    logger.debug("Entered root endpoint")
    return {"message": "Welcome to the Automation API"}



