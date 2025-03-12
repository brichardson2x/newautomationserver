from fastapi import APIRouter, Depends
from app.schemas.user import UserSchema, UserResponse
from app.services.user import UserService
from app.core.logging import setup_logging
from app.dependencies import read_security

logger = setup_logging()

router = APIRouter(dependencies=[Depends(read_security)])

@router.post("/user/create", response_model=UserResponse)
async def create_user(user: UserSchema):
    logger.debug("Entered create_user endpoint")
    user = UserService(user)
    return await user.create_user()