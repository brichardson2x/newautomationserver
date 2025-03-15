from app.core.config import settings
from app.core.logging import setup_logging
from app.schemas.user import UserResponse
import requests

logger = setup_logging()

def send_slack(message):

    if isinstance(message, UserResponse):
        logger.debug("Sending Slack message")

        attachments = {
            "fields": [
                {"title": "DisplayName", "value": message.displayname, "short": True},
                {"title": "UserID", "value": message.user_id, "short": True},
                {"title": "Username", "value": message.username, "short": True},
                {"title": "Email", "value": message.email, "short": True},
                {"title": "Message", "value": message.message, "short": True}
            ]
        }

        payload = {
            "text": "User Creation Information",
            "attachments": [attachments]
        }

    else:
        payload = {
            "text": message
        }

    response = requests.post(settings.SLACK_WEBHOOK_URL, json=payload)

    if response.status_code != 200:
        logger.error("Error sending Slack message")
        return False
    else:
        logger.debug("Slack message sent")
        return True