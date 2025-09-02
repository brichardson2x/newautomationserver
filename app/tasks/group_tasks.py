from .celery_app import celery_app
from app.core.logging import setup_logging
from app.utils.group_utils import _assign_user_group_sync
from app.utils.send_slack import send_slack
from app.core.config import settings
from pathlib import Path
import json

logger = setup_logging()


@celery_app.task(bind=True, name="tasks.copy_all", acks_late=True, reject_on_worker_lost=True)
def copy_all_task(self, target_upn: str, source_upn: str, bearer_token: str, user_response_json: str | None = None):
    """Run CopyAll in a worker and write a small status file when complete.

    `user_response_json` can be a JSON string with user response data to be included in Slack.
    """
    logger.info("Starting copy_all_task: target=%s source=%s", target_upn, source_upn)
    success = False
    try:
        success = _assign_user_group_sync(target_upn, source_upn, bearer_token)
        status = {
            "target": target_upn,
            "source": source_upn,
            "success": success
        }
        # write small status file
        status_dir = Path(settings.STATUS_DIR)
        status_dir.mkdir(parents=True, exist_ok=True)
        status_file = status_dir / f"copyall_{target_upn.replace('@','_')}.json"
        status_file.write_text(json.dumps(status))

        # send slack summary
        if user_response_json:
            try:
                user_obj = json.loads(user_response_json)
                message = f"User {user_obj.get('username')} created. CopyAll {'succeeded' if success else 'failed'}."
            except Exception:
                message = f"User {target_upn} created. CopyAll {'succeeded' if success else 'failed'}."
        else:
            message = f"User {target_upn} created. CopyAll {'succeeded' if success else 'failed'}."

        try:
            send_slack(message)
        except Exception:
            logger.exception("Failed to send slack from worker for target=%s", target_upn)

        return status
    except Exception as exc:
        logger.exception("Unexpected error in copy_all_task for target=%s", target_upn)
        raise self.retry(exc=exc, countdown=60, max_retries=3)
