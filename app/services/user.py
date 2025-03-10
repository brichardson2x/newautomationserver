from app.core.logging import setup_logging
from app.core.config import settings
from app.schemas.user import UserSchema, UserResponse
from app.utils.generate_token import generate_token
import requests
import os
import subprocess

logger = setup_logging()

def find_user_params(user_displayname: str):
    logger.debug("Setting up params for finding user by ID")
    params = {
        '$filter': f"displayName eq '{user_displayname}'",
        '$top': '1',
        '$expand': 'manager'
    }
    return params

def assign_manager_request(user_id: str, manager_id: str):
    logger.debug("Assigning manager")
    return {
        "@odata.id": f"{settings.MS_API_URL}/users/{user_id}/manager/$ref"
    }

def assign_license_request(user_id: str):
    logger.debug("Assigning license")
    add_licenses = [{"disabledPlans": [], "skuId": license["skuId"]} for license in settings.ASSIGNED_LICENSES]
    return {
        "addLicenses": add_licenses,
        "removeLicenses": []
    }

def assign_user_group(user_name: str, cloned_user: str, bearer_token: str):
    logger.debug("Assigning user to group")
    try:
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "CopyGroups.ps1")
        command = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", script_path, bearer_token, settings.SERVICE_ACCOUNT, settings.SERVICE_ACCOUNT_PASSWORD, user_name, cloned_user]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        logger.debug(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error assigning user to group: {e}")
        return False
    except FileNotFoundError as e:
        logger.error(f"Error finding script: {e}")
        return False




class User:
    def __init__(self, user: UserSchema):
        logger.debug("Setting up User")
        self.user = user

    def create_user(self):
        logger.debug("Creating user")
        ms_token = generate_token()
        headers = {
            "Authorization": f"Bearer {ms_token}",
            "Content-Type": "application/json"
        }
        url = f"{settings.MS_API_URL}/users"
        params = find_user_params(f"{self.user.displayname}")

        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            logger.debug("User already exists")
            userdata = response.json()
            user_response = UserResponse(
                username=userdata["value"][0]["userPrincipalName"],
                email=userdata["value"][0]["mail"],
                user_id=userdata["value"][0]["id"],
                displayname=userdata["value"][0]["displayName"],
                message="User already exists"
            )
        else:
            logger.debug("Creating user")

            request = {
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
            userdata = requests.post(url, headers=headers, json=request)
            user_response = UserResponse(
                username=userdata["value"][0]["userPrincipalName"],
                email=userdata["value"][0]["mail"],
                user_id=userdata["value"][0]["id"],
                displayname=userdata["value"][0]["displayName"],
                message="User already exists"
            )
            if self.user.manager_id is not None:
                params = find_user_params(self.user.manager)
                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    logger.debug("Manager found")
                    user_response.message += "\nManager found"
                    manager = response.json()
                    self.user.manager_id = manager["value"][0]["id"]

                    manager_request = assign_manager_request(user_response.user_id, self.user.manager_id)
                    response = requests.put(url, headers=headers, json=manager_request)
                    if response.status_code == 204:
                        logger.debug("Manager assigned")
                        user_response.message += "\nManager assigned"
                    else:
                        logger.error("Manager not assigned")
                        user_response.message += "\nManager not assigned"
                else:
                    logger.error("Manager not found")
                    user_response.message += "\nManager not found"


            license_request = assign_license_request(user_response.user_id)
            response = requests.post(url, headers=headers, json=license_request)
            if response.status_code == 200:
                logger.debug("License assigned")
                user_response.message += "\nLicense assigned"
            else:
                logger.error("License not assigned")
                user_response.message += "\nLicense not assigned"
            
            # Calling the function to assign the user to a group
            group_result = assign_user_group(user_response.username, self.user.cloned_user, ms_token)
            if group_result:
                logger.debug("User assigned to groups")
                user_response.message += "\nUser assigned to groups"
            else:
                logger.error("User not assigned to groups")
                user_response.message += "\nUser not assigned to groups"

        return user_response