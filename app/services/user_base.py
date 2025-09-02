from app.core.logging import setup_logging
from app.schemas.user import UserSchema

logger = setup_logging()


class UserServiceBase:
    """Small common base for user services.

    Keep shared initialization and light helpers here so create/remove services
    can stay focused and easier to test.
    """
    def __init__(self, user: UserSchema):
        logger.debug("Initializing UserServiceBase")
        self.user = user
