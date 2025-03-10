from fastapi import APIRouter
from app.schemas.user import UserSchema, UserResponse
from app.services.user import UserService
from app.core.logging import setup_logging

logger = setup_logging()

router = APIRouter()

@router.post("/user/create", response_model=UserResponse)
async def create_user(user: UserSchema):
    logger.debuf("Entered create_user endpoint")
    user = UserService(user)
    return user.create_user()