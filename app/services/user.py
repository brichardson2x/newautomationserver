from app.core.logging import setup_logging
from app.core.config import settings
from app.schemas.user import UserSchema, UserResponse
from app.utils.send_slack import send_slack
from app.utils.generate_token import generate_token
from fastapi import HTTPException
from pathlib import Path
import requests
import os
import subprocess
import json



logger = setup_logging()

def find_user_params(user_displayname: str):
    logger.debug("Setting up params for finding user by ID")
    params = {
        '$filter': f"displayName eq '{user_displayname}'",
        '$top': '1',
        '$expand': 'manager'
    }
    return params

def assign_manager_request(manager_id: str):
    logger.debug("Assigning manager")
    return {
        "@odata.id": f"{settings.MS_API_URL}/users/{manager_id}"
    }

#def assign_license_request(user_id: str):
    logger.debug("Assigning license")
    add_licenses = [{"disabledPlans": [], "skuId": license["skuId"]} for license in settings.ASSIGNED_LICENSES]
    return {
        "addLicenses": add_licenses,
        "removeLicenses": []
    }

#def assign_license_request(user_id: str):
    logger.debug("Assigning license")

    assigned_licenses = json.loads(settings.ASSIGNED_LICENSES)
    
    add_licenses = [{"disabledPlans": license.get("disabledPlans", []), "skuId": license["skuId"]} for license in assigned_licenses]
    
    return {
        "addLicenses": add_licenses,
        "removeLicenses": []
    }

def assign_license_request(user_id: str):
    logger.debug("Assigning license")
    add_licenses = settings.ASSIGNED_LICENSES
    return add_licenses

def assign_user_group(user_name: str, cloned_user: str, bearer_token: str):
    logger.debug("Assigning user to group")
    try:
        script_path = Path(__file__).resolve().parent.parent / "scripts" / "CopyGroups.ps1"
        command = ["pwsh.exe", "-ExecutionPolicy", "Bypass", "-File", script_path, bearer_token, settings.SERVICE_ACCOUNT, settings.SERVICE_ACCOUNT_PASSWORD, user_name, cloned_user]
        #result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        
        subprocess.run(command, capture_output=True, text=True, check=True)
        #result = subprocess.run(command, text=True, check=True)

        #logger.debug(result.stdout)
        #logger.debug(result.stderr)

        #if result.stderr:
            #logger.error(result.stderr)
            #raise Exception(result.stderr)
        return True
    
        #for line_out in result.stdout:
            #logger.debug(line_out.strip())



        #result.wait()
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error assigning user to group")
        return False
    except FileNotFoundError as e:
        logger.error(f"Error finding script")
        return False
    except Exception as e:
        logger.error(f"Unexecpected error assigning user to group")
        return False




class UserService:
    def __init__(self, user: UserSchema):
        logger.debug("Setting up User")
        self.user = user

    async def create_user(self):
        logger.debug("Creating user")
        ms_token = await generate_token()

        headers = {
            "Authorization": f"Bearer {ms_token}",
            "Content-Type": "application/json"
        }
        url = f"{settings.MS_API_URL}/users"
        params = find_user_params(f"{self.user.displayname}")

        response = requests.get(url, headers=headers, params=params)

        logger.debug(response.status_code)

        if response.status_code == 200 and response.json()["value"]:
            logger.debug("User already exists")
            userdata = response.json()
            logger.debug(userdata)
            user_response = UserResponse(
                username=userdata["value"][0]["userPrincipalName"],
                email=userdata["value"][0]["mail"],
                user_id=userdata["value"][0]["id"],
                displayname=userdata["value"][0]["displayName"],
                message="User already exists"
            )
        elif 400 <= response.status_code < 500:
            logger.debug("No permission in Microsoft")
            raise HTTPException(status_code=403, detail="Please check your Microsoft app permissions")
        else:
            logger.debug("Creating user")

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
                user_response = UserResponse(
                    username=userdata.get("userPrincipalName"),
                    email=userdata.get("mail"),
                    user_id=userdata.get("id"),
                    displayname=userdata.get("displayName"),
                    message="User created"
                )
                logger.debug(user_response)
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
            
            if self.user.manager is not None:
                params = find_user_params(self.user.manager)
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
                    manager_request = assign_manager_request(self.user.manager_id)
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


            license_request = assign_license_request(user_response.user_id)
            url = f"{settings.MS_API_URL}/users/{user_response.user_id}/assignLicense"

            response = requests.post(url, headers=headers, data=license_request)
            logger.debug(response.status_code)
            logger.debug(response.json())
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
                user_response.message += ". License not assigned due to Microsoft Server Error, please addlicenses manually"
            
            # Calling the function to assign the user to a group
            if self.user.cloned_user is not None:
                group_result = assign_user_group(user_response.username, self.user.cloned_user, ms_token)
                if group_result:
                    logger.debug("User assigned to groups")
                    user_response.message += ". User was assigned to groups"
                else:
                    logger.error("User not assigned to groups")
                    user_response.message += ". User could not be assigned to groups"
            else: 
                logger.debug("No cloned user")
                user_response.message += ". No cloned user, so no groups assigned"

        send_slack(user_response)
        
        logger.info("User process finished")

        return user_response
    