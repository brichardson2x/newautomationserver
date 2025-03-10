from pydantic import BaseModel, model_validator
from typing import Optional, Dict
from app.core.logging import setup_logging
from app.core.config import settings

logger = setup_logging()

def generate_email(firstname: str, lastname: str, domain: str = "daxko.com") -> str:
    logger.debug("Generating email")
    return f"{firstname.lower()}.{lastname.lower()}@{domain}"

class UserSchema(BaseModel):
    logger.debug("Setting up UserSchema")
    user_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    domain: str = settings.DEFAULT_DOMAIN
    title: Optional [str] = None
    department: Optional[str] = None
    firstname: str
    lastname: str
    middle_name: Optional[str] = None
    manager: Optional[str] = None
    cloned_user: Optional[str] = None
    groups: Optional[Dict] = None
    password: str = settings.DEFAULT_PASSWORD

    @model_validator(mode="after")
    def set_email_username(self):
        logger.debug("Checking email and username")
        generated = generate_email(self.firstname, self.lastname)
        if self.email is None:
            self.email = generated

        if self.username is None:
            self.username = generated
            
        return self