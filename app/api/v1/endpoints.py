from fastapi import APIRouter
from schemas.user import UserSchema, UserResponse
from services.user import UserService

router = APIRouter()

@router.post("/user", response_model=UserResponse)
async def create_user(user: UserSchema):
    user = UserService(user)
    return user.create_user()