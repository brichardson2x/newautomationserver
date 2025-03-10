from pydantic import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Automation App"
    API_SECRET_KEY: str
    MS_TENANT_ID: str
    MS_API_CLIENT_ID: str
    MS_API_CLIENT_SECRET: str
    MS_API_URL: str = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    MS_API_SCOPE: str = "https://graph.microsoft.com/.default"


    class Config:
        env_file = ".env"

settings = Settings()