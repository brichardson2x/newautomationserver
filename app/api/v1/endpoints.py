from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.schemas.user import UserSchema, UserResponse
from app.services.user import UserService
from app.core.logging import setup_logging
from app.dependencies import read_security

logger = setup_logging()

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(dependencies=[Depends(read_security)])

async def add_middleware(app):
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, lambda _: JSONResponse(
        status_code=429, content={"message": "Too many requests, slow down!"}
    ))
    app.add_middleware(SlowAPIMiddleware)

@router.post("/user/create", response_model=UserResponse)
@limiter.limit("7/minute")
async def create_user(request: Request, user: UserSchema):
    logger.debug("Entered create_user endpoint")
    user = UserService(user)
    return await user.create_user()