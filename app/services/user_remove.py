from app.core.logging import setup_logging
from app.schemas.user import UserSchema

logger = setup_logging()


class UserRemoveService:
    def __init__(self, user: UserSchema):
        logger.debug("Setting up UserRemoveService")
        self.user = user

    async def remove_user(self):
        """Stub for remove user flow. Implement offboarding steps here:

        - remove from groups
        - disable account
        - archive or remove mailbox
        - write audit record
        """
        logger.debug("remove_user called (stub)")
        return None
