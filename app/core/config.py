from pydantic_settings import BaseSettings
from typing import Any
from pathlib import Path
from app.core.logging import setup_logging

logger = setup_logging()
BASE_DIR = Path(__file__).resolve().parent.parent

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
    SLACK_WEBHOOK_URL: str

    class Config:
        env_file = BASE_DIR /  ".env"
        env_file_encoding = "utf-8"

settings = Settings()