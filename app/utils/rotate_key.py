from generate_token import generate_token
from app.core.config import settings
import random
import requests
import os
from app.core.logging import setup_logging

logger = setup_logging()

async def rotate_key():
    logger.debug("Rotating key")
    token = await generate_token()
    headers = {"Authorization": f"Bearer {token}"}, {"Content-Type": "application/json"}
    url = f"{settings.MS_API_URL}/applications/{settings.MS_API_CLIENT_ID}/addPassword"
    request = {
        "passwordCredential": {
            "displayName": f"key_rotation{random.randint(100, 12000)}",
            "endDateTime": "2022-12-31T00:00:00Z"
        }
    }

    response = requests.post(url, headers=headers, json=request)
    if response.status_code == 201:
        logger.debug("Key rotated")
        return response.json()["secretText"]
    elif 400 <= response.status_code < 500:
        logger.error("Error rotating key due to permissions")
        return None
    else:
        logger.error("Error rotating key")
        return None
    
async def update_environment():
    logger.debug("Updating environment")
    
    if os.path.exists("app/.env"):
        with open("app/.env", "r") as f:
            f.write(f"MS_API_CLIENT_SECRET={await rotate_key()}")