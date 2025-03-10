import httpx
from app.core.config import settings
from fastapi import HTTPException
from app.core.logging import setup_logging

logger = setup_logging()

async def generate_token():
    logger.debug("Generating token")

    url = settings.MS_API_TOKEN_URL.format(tenant_id=settings.MS_TENANT_ID)
    payload = {
        "client_id": settings.MS_API_CLIENT_ID,
        "scope": settings.MS_API_SCOPE,
        "client_secret": settings.MS_API_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }


    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, data=payload)
            response.raise_for_status()
            logger.debug("Token generated")
            return response.json().get("access_token")
        except Exception as e:
            logger.error(f"Error generating token: {e}")
            raise HTTPException(status_code=500, detail="Error generating token")