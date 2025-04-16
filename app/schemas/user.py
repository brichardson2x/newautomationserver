from pydantic import BaseModel, model_validator, EmailStr
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
    username: Optional[EmailStr] = None
    nickname: Optional[str] = None
    email: Optional[EmailStr] = None
    domain: str = settings.DEFAULT_DOMAIN
    title: Optional [str] = None
    department: Optional[str] = None
    displayname: Optional[str] = None
    firstname: str
    lastname: str
    middle_name: Optional[str] = None
    manager: Optional[str] = None
    manager_id: Optional[str] = None
    cloned_user: Optional[str] = None
    groups: Optional[Dict] = None
    password: str = settings.DEFAULT_PASSWORD
    autoreply: Optional[str] = None
    shared_mailbox: Optional[str] = None
    shared_onedrive: Optional[str] = None

    @model_validator(mode="after")
    def set_email_username(self):
        logger.debug("Checking email and username")
        generated = generate_email(self.firstname, self.lastname)
        if self.email is None:
            self.email = generated

        if self.username is None:
            self.username = generated

        if self.nickname is None:
            self.nickname = self.username.split("@")[0]
        
        if self.displayname is None:
            self.displayname = f"{self.firstname} {self.lastname}"
            
        return self

    @model_validator(mode="after")
    def name_cleanup(self):
        logger.debug("Cleaning up names")
        
        self.shared_mailbox = self.shared_mailbox.replace(" ","")
        self.shared_onedrive = self.shared_onedrive.replace(" ","")
        
        if "." in self.shared_mailbox:
            self.shared_mailbox = self.shared_mailbox.replace(".", " ")
        if "." in self.shared_onedrive:
            self.shared_onedrive = self.shared_onedrive.replace(".", " ")

        if "," in self.shared_mailbox:
            self.shared_mailbox = self.shared_mailbox.split(",")[0]
        if "," in self.shared_onedrive:
            self.shared_onedrive = self.shared_onedrive.split(",")[0]
        


        return self
    
class UserResponse(BaseModel):
    logger.debug("Setting up UserResponse")
    username: str
    email: str
    user_id: str
    displayname: str
    message: Optional[str] = None
    
    class Config:
        json_encoders = {
            type(None): lambda v: None  # Explicitly serialize None as null
        }