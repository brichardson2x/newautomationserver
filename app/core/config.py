from pydantic_settings import BaseSettings
import os
from app.core.logging import setup_logging

logger = setup_logging()

class Settings(BaseSettings):
    logger.debug("Setting up Settings")
    APP_NAME: str = "Automation App"
    API_SECRET_KEY: str
    MS_TENANT_ID: str
    MS_API_CLIENT_ID: str
    MS_API_CLIENT_SECRET: str
    MS_API_URL: str = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    MS_API_SCOPE: str = "https://graph.microsoft.com/.default"
    DEFAULT_PASSWORD: str
    DEFAULT_DOMAIN: str

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

settings = Settings()