from pydantic_settings import BaseSettings
from typing import Dict, List, Any
import os
from app.core.logging import setup_logging

logger = setup_logging()

class Settings(BaseSettings):
    logger.debug("Setting up Settings")
    APP_NAME: str = "Automation App"
    VERSION: str = "0.1.0"
    API_SECRET_KEY: str
    MS_TENANT_ID: str
    MS_API_CLIENT_ID: str
    MS_API_CLIENT_SECRET: str
    MS_API_TOKEN_URL: str = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    MS_API_URL: str = "https://graph.microsoft.com/v1.0"
    MS_API_SCOPE: str = "https://graph.microsoft.com/.default"
    DEFAULT_PASSWORD: str
    DEFAULT_DOMAIN: str
    ASSIGNED_LICENSES: Any
    SERVICE_ACCOUNT: str
    SERVICE_ACCOUNT_PASSWORD: str
    FASTAPI_DEBUG: bool
    FASTAPI_HOST: str
    FASTAPI_PORT: int

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

settings = Settings()