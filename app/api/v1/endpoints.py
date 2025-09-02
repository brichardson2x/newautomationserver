from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.schemas.user import UserSchema, UserResponse
from app.services.user import UserService
from app.core.logging import setup_logging
from app.dependencies import read_security
from app.core.config import settings
from fastapi.responses import FileResponse
from pathlib import Path

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
async def create_user(request: Request, user: UserSchema, background_tasks: BackgroundTasks):
    logger.debug("Entered create_user endpoint")
    service = UserService(user)
    return await service.create_user(background_tasks=background_tasks)


@router.post("/user/remove")
@limiter.limit("7/minute")
async def remove_user(request: Request, user: UserSchema):
    """Remove a user (not implemented in service yet).

    Returns 501 Not Implemented until service logic is added.
    """
    logger.debug("Entered remove_user endpoint")
    service = UserService(user)
    result = await service.remove_user()
    # remove_user is a stub; return 501 for now
    return JSONResponse(status_code=501, content={"message": "remove_user not implemented"})


@router.get("/user/status/{target_upn}")
async def get_user_status(target_upn: str):
    """Return a small JSON status file written by the background worker after CopyAll finishes.

    The status files are written to the directory configured by `settings.STATUS_DIR`.
    """
    status_dir = Path(settings.STATUS_DIR)
    status_file = status_dir / f"copyall_{target_upn.replace('@','_')}.json"
    if not status_file.exists():
        return JSONResponse(status_code=404, content={"message": "Status not found"})
    return FileResponse(status_file)