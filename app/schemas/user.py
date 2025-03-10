from pydantic import BaseModel
from typing import Optional, Dict
from app.core.logging import setup_logging
logger = setup_logging()

def generate_email(firstname: str, lastname: str, domain: str = "daxko.com") -> str:
    logger.debug("Generating email")
    return f"{firstname.lower()}.{lastname.lower()}@{domain}"

class UserSchema(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    domain: str = "daxko.com"
    title: Optional [str] = None
    department: Optional[str] = None
    firstname: str
    lastname: str
    middle_name: Optional[str] = None
    manager: Optional[str] = None
    groups: Optional[Dict] = None

testjson = {"hey": "what", "getit": "who"}
test = UserSchema(firstname="test", lastname="test2", groups=testjson)
print(test.groups)