from app.core.logging import setup_logging
from app.core.config import settings
from pathlib import Path
import subprocess
from fastapi import BackgroundTasks
from typing import Optional
import asyncio
from app.utils.send_slack import send_slack

logger = setup_logging()


def _assign_user_group_sync(user_name: str, cloned_user: str, bearer_token: str) -> bool:
    """Run the PowerShell `CopyAll.ps1` script synchronously to copy all data from
    the cloned user to the new user.

    Note: `user_name` and `cloned_user` must be UPNs (userPrincipalName), e.g.
    "alice@example.com". This function streams stdout/stderr from the PowerShell
    process into the application logger so you can observe progress in real time.

    Returns True on success (exit code 0), False otherwise.
    """
    logger.debug("Assigning user (CopyAll) from cloned user (sync). target=%s source=%s", user_name, cloned_user)
    script_path = Path(__file__).resolve().parent.parent / "scripts" / "CopyAll.ps1"
    if not script_path.exists():
        logger.error("CopyAll script not found at %s", script_path)
        return False

    command = [
        "pwsh.exe",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
        bearer_token,
        settings.SERVICE_ACCOUNT,
        settings.SERVICE_ACCOUNT_PASSWORD,
        user_name,    # target UPN
        cloned_user,  # source UPN
    ]

    try:
        # Use Popen so we can stream output lines into our logger as they appear.
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        # Stream lines to logger (info level) so they show up in your app logs.
        if proc.stdout is not None:
            for line in proc.stdout:
                logger.info("[CopyAll] %s", line.rstrip())

        proc.wait()
        if proc.returncode == 0:
            logger.debug("CopyAll finished successfully for target=%s", user_name)
            return True
        else:
            logger.error("CopyAll exited with code %s for target=%s", proc.returncode, user_name)
            return False
    except FileNotFoundError:
        logger.error("pwsh.exe or script not found when running CopyAll")
        return False
    except Exception:
        logger.exception("Unexpected error when running CopyAll for target=%s", user_name)
        return False


async def _assign_user_group_async(user_name: str, cloned_user: str, bearer_token: str) -> bool:
    """Async wrapper that runs the blocking subprocess call in the default executor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _assign_user_group_sync, user_name, cloned_user, bearer_token)


async def _assign_user_group_background(user_name: str, cloned_user: str, bearer_token: str, user_response_json: Optional[str] = None) -> None:
    """BackgroundTasks wrapper that awaits the async worker and logs errors.

    This ensures the BackgroundTasks system does not block the event loop while running
    the long-running PowerShell subprocess (which executes in an executor).
    """
    try:
        success = await _assign_user_group_async(user_name, cloned_user, bearer_token)
        if not success:
            logger.error("Background group assignment failed for %s", user_name)
        # Build and send slack message here so notification occurs after the copy finishes
        try:
            if user_response_json:
                send_slack(user_response_json)
            else:
                msg = f"User {user_name} group copy {'succeeded' if success else 'failed'}"
                send_slack(msg)
        except Exception:
            logger.exception("Failed to send slack from background task for %s", user_name)
    except Exception:
        logger.exception("Unexpected exception while running background group assignment for %s", user_name)


def schedule_assign_user_group(background_tasks: Optional[BackgroundTasks], user_name: str, cloned_user: str, bearer_token: str, user_response_json: Optional[str] = None) -> bool:
    """Schedule the group assignment.

    If `background_tasks` is provided, schedule the copy and return True (scheduled).
    If not, run synchronously and return the boolean success result.
    """
    if background_tasks is not None:
        logger.debug("Scheduling assign_user_group as a background task")
        background_tasks.add_task(_assign_user_group_background, user_name, cloned_user, bearer_token, user_response_json)
        return True
    else:
        logger.debug("Running assign_user_group synchronously (no BackgroundTasks provided)")
        # If caller wants async, they can call _assign_user_group_async directly
        return _assign_user_group_sync(user_name, cloned_user, bearer_token)
