from app.core.logging import setup_logging
from app.core.config import settings
from app.schemas.user import UserSchema, UserResponse
from app.utils.send_slack import send_slack
from app.utils.generate_token import generate_token
from app.utils.group_utils import schedule_assign_user_group
from fastapi import HTTPException
from fastapi import BackgroundTasks
import requests
import json

logger = setup_logging()


class UserCreateService:
    def __init__(self, user: UserSchema):
        logger.debug("Setting up UserCreateService")
        self.user = user

    # --- Private helper: build params for MS Graph queries ---
    def _find_user_params(self, user_displayname: str):
        logger.debug("Setting up params for finding user by ID")
        params = {
            '$filter': f"displayName eq '{user_displayname}'",
            '$top': '1',
            '$expand': 'manager'
        }
        return params

    # --- Private helper: manager request payload ---
    def _assign_manager_request(self, manager_id: str):
        logger.debug("Assigning manager")
        return {
            "@odata.id": f"{settings.MS_API_URL}/users/{manager_id}"
        }

    # --- Private helper: build license payload ---
    def _make_license_payload(self, user_id: str):
        logger.debug("Assigning license")
        try:
            if isinstance(settings.ASSIGNED_LICENSES, str):
                assigned_licenses = json.loads(settings.ASSIGNED_LICENSES)
            else:
                assigned_licenses = settings.ASSIGNED_LICENSES
        except Exception:
            # Fallback: treat as already-structured
            assigned_licenses = settings.ASSIGNED_LICENSES

        add_licenses = [
            {"disabledPlans": license.get("disabledPlans", []), "skuId": license["skuId"]}
            for license in assigned_licenses
        ]

        payload = {"addLicenses": add_licenses, "removeLicenses": []}
        return json.dumps(payload)


    # --- Helper function: Check if user exists ---
    async def _check_user_exists(self, headers, url, params):
        response = requests.get(url, headers=headers, params=params)
        logger.debug(response.status_code)
        if response.status_code == 200 and response.json()["value"]:
            logger.debug("User already exists")
            userdata = response.json()
            logger.debug(userdata)
            return UserResponse(
                username=userdata["value"][0]["userPrincipalName"],
                email=userdata["value"][0]["mail"],
                user_id=userdata["value"][0]["id"],
                displayname=userdata["value"][0]["displayName"],
                message="User already exists"
            )
        elif 400 <= response.status_code < 500:
            logger.debug("No permission in Microsoft")
            raise HTTPException(status_code=403, detail="Please check your Microsoft app permissions")
        return None

    # --- Helper function: Create user ---
    async def _create_user(self, headers, url):
        o_request = {
            "accountEnabled": True,
            "displayName": self.user.displayname,
            "mailNickname": self.user.nickname,
            "userPrincipalName": self.user.username,
            "passwordProfile": {
                "forceChangePasswordNextSignIn": True,
                "password": self.user.password
            },
            "department": self.user.department,
            "usageLocation": "US",
            "jobTitle": self.user.title,
            "givenName": self.user.firstname,
            "surname": self.user.lastname,
            "mail": self.user.email,
        }
        request = json.dumps(o_request)
        logger.debug(request)
        userdata = requests.post(url, headers=headers, data=request)
        logger.debug(userdata.json())
        logger.debug(userdata.request)
        logger.debug(userdata.status_code)
        if userdata.status_code == 201:
            logger.debug("User created")
            userdata = userdata.json()
            return UserResponse(
                username=userdata.get("userPrincipalName"),
                email=userdata.get("mail"),
                user_id=userdata.get("id"),
                displayname=userdata.get("displayName"),
                message="User created"
            )
        elif userdata.status_code == 400:
            logger.error("User not created due to invalid data, usually a password without sufficient complexity")
            send_slack("User could not be created due to invalid data, usually a password without sufficient complexity")
            raise HTTPException(status_code=400, detail="User could not be created due to invalid data, usually a password without sufficient complexity")
        elif 401 <= userdata.status_code < 500:
            logger.error("User not created due to permissions")
            send_slack("User could not be created due to permissions, please check your Microsoft app permissions")
            raise HTTPException(status_code=403, detail="Please check your Microsoft app permissions")
        else:
            logger.error("User not created due to Microsoft Server Error")
            send_slack("User could not be created due to Microsoft Server Error, try again later")
            raise HTTPException(status_code=500, detail="User could not be created due to Microsoft Server Error, try again later")

    # --- Helper function: Assign manager ---
    async def _assign_manager(self, headers, user_response):
        if self.user.manager is not None:
            url = f"{settings.MS_API_URL}/users"
            params = self._find_user_params(self.user.manager)
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200 and response.json().get("value", []):
                logger.debug("Manager found")
                user_response.message += ". Manager found"
                manager = response.json()
                self.user.manager_id = manager["value"][0]["id"]
                logger.debug(self.user.manager_id)
                logger.debug(user_response.user_id)
                url = f"{settings.MS_API_URL}/users/{user_response.user_id}/manager/$ref"
                logger.debug(url)
                manager_request = self._assign_manager_request(self.user.manager_id)
                manager_request = json.dumps(manager_request)
                logger.debug(manager_request)
                response = requests.put(url, headers=headers, data=manager_request)
                if response.status_code == 204:
                    logger.debug("Manager assigned")
                    user_response.message += ". Manager assigned"
                elif 400 <= response.status_code < 500:
                    logger.error("Manager not assigned due to permissions")
                    user_response.message += ". Manager not assigned due to permissions in Entra App"
                else:
                    logger.error("Manager not assigned due to Microsoft Server Error")
                    user_response.message += ". Manager not assigned due to Microsoft Server Error"
            else:
                logger.error("Manager not found")
                user_response.message += ". Manager not found"
        else:
            logger.debug("No manager assigned")
            user_response.message += ". No manager assigned"

    # --- Helper function: Assign license ---
    async def _assign_license(self, headers, user_response):
        """Attempt to assign licenses but never raise HTTP errors.

        This method will log failures and append to `user_response.message` so
        the overall create flow continues even if license assignment fails.
        """
        license_request = self._make_license_payload(user_response.user_id)
        url = f"{settings.MS_API_URL}/users/{user_response.user_id}/assignLicense"
        try:
            response = requests.post(url, headers=headers, data=license_request)
        except Exception:
            logger.exception("Failed to contact MS Graph for license assignment")
            user_response.message += ". License assignment could not be attempted due to a network error"
            return

        logger.debug("License assign response: %s", getattr(response, 'status_code', 'no-code'))
        # Try to safely inspect JSON body without raising
        try:
            logger.debug(response.json())
        except Exception:
            logger.debug("License assign response had no JSON body")

        if response.status_code == 200:
            logger.debug("License assigned")
            user_response.message += ". License assigned"
        elif response.status_code == 400:
            logger.error("License not assigned due to invalid data")
            user_response.message += ". License that was requested is not a valid Microsoft license SKU"
        elif 401 <= response.status_code < 500:
            logger.error("License not assigned due to permissions")
            user_response.message += ". License not assigned due to permissions in Entra App"
        else:
            logger.error("License not assigned due to Microsoft Server Error")
            user_response.message += ". License not assigned due to Microsoft Server Error, please add licenses manually"

    # --- Helper function: Assign user to groups ---
    async def _assign_groups(self, user_response, ms_token, background_tasks: BackgroundTasks | None = None):
        # If no cloned user provided, skip group assignment
        if self.user.cloned_user is None:
            logger.debug("No cloned user")
            user_response.message += ". No cloned user, so no groups assigned"
            return

        # If Celery is configured, enqueue the copy job to a worker and return immediately
        # Prepare user_response_json for background consumers (Celery or BackgroundTasks)
        user_json = json.dumps(user_response.model_dump()) if hasattr(user_response, 'model_dump') else None
        if settings.CELERY_BROKER_URL:
            try:
                # enqueue the task; pass user_response JSON so worker can send slack
                from app.tasks.group_tasks import copy_all_task
                copy_all_task.apply_async(args=(user_response.username, self.user.cloned_user, ms_token, user_json))
                logger.debug("Enqueued copy_all_task via Celery for target=%s", user_response.username)
                user_response.message += ". Group copy enqueued"
                return
            except Exception:
                logger.exception("Failed to enqueue Celery copy_all_task; falling back to BackgroundTasks/sync")

        # Otherwise, use BackgroundTasks scheduling or synchronous fallback
        group_result = schedule_assign_user_group(background_tasks, user_response.username, self.user.cloned_user, ms_token, user_json)
        if group_result:
            logger.debug("User assigned to groups or scheduled")
            user_response.message += ". User was assigned to groups"
        else:
            logger.error("User not assigned to groups")
            user_response.message += ". User could not be assigned to groups"

    # --- Main create_user function, now split into helpers ---
    async def create_user(self, background_tasks: BackgroundTasks | None = None):
        logger.debug("Creating user")
        ms_token = await generate_token()
        headers = {
            "Authorization": f"Bearer {ms_token}",
            "Content-Type": "application/json"
        }
        url = f"{settings.MS_API_URL}/users"
        params = self._find_user_params(f"{self.user.displayname}")

        # Check if user exists
        user_response = await self._check_user_exists(headers, url, params)
        if not user_response:
            # Create user
            user_response = await self._create_user(headers, url)
            # Assign manager
            await self._assign_manager(headers, user_response)
            # Assign license
            await self._assign_license(headers, user_response)
            # Assign groups (may be scheduled)
            await self._assign_groups(user_response, ms_token, background_tasks)

        # Slack notification will be sent by the background worker (CopyAll) or Celery task
        logger.info("User process finished; background tasks (if any) may be running")
        return user_response
