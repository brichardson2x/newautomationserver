from app.core.logging import setup_logging

logger = setup_logging()

def generate_email(user):
    logger.debug("Generating email")
    email = f"{user.firstname}.{user.lastname}@{user.domain}"
    logger.debug("Email generated")
    return email