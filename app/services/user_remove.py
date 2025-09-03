from app.core.logging import setup_logging
from app.schemas.user import UserSchema, UserResponse
from app.core.config import settings
from app.utils.generate_token import generate_token
from app.utils.send_slack import send_slack
from typing import Optional, List
import requests
import json

logger = setup_logging()


class UserRemoveService:
    def __init__(self, user: UserSchema):
        logger.debug("Setting up UserRemoveService")
        self.user = user

    def _find_user_params(self, user_identifier: str):
        """Build MS Graph query params to locate a user by UPN or display name."""
        # Prefer exact match on userPrincipalName if it looks like an email
        if "@" in (user_identifier or ""):
            filter_str = f"userPrincipalName eq '{user_identifier}'"
        else:
            filter_str = f"displayName eq '{user_identifier}'"

        return {
            '$filter': filter_str,
            '$top': '1'
        }

    async def _get_user(self, headers) -> Optional[dict]:
        """Return user JSON from Graph or None."""
        # If user_id was provided, fetch directly
        if self.user.user_id:
            url = f"{settings.MS_API_URL}/users/{self.user.user_id}"
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            logger.debug("Could not fetch user by id: %s", resp.status_code)
            return None

        # otherwise try by username then displayname
        candidates = [self.user.username, self.user.displayname]
        for candidate in candidates:
            if not candidate:
                continue
            url = f"{settings.MS_API_URL}/users"
            params = self._find_user_params(candidate)
            resp = requests.get(url, headers=headers, params=params)
            if resp.status_code == 200 and resp.json().get('value'):
                return resp.json()['value'][0]
            elif 400 <= resp.status_code < 500:
                logger.error("Permission error finding user: %s", resp.status_code)
                return None

        logger.debug("User not found by provided identifiers")
        return None

    async def _disable_account(self, headers, user_id: str) -> bool:
        url = f"{settings.MS_API_URL}/users/{user_id}"
        payload = json.dumps({"accountEnabled": False})
        resp = requests.patch(url, headers=headers, data=payload)
        if resp.status_code in (200, 204):
            logger.debug("Disabled account for user %s", user_id)
            return True
        logger.error("Failed to disable account %s: %s", user_id, getattr(resp, 'status_code', None))
        return False

    async def _get_assigned_license_skus(self, headers, user_id: str) -> List[str]:
        url = f"{settings.MS_API_URL}/users/{user_id}?$select=assignedLicenses"
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            try:
                assigned = resp.json().get('assignedLicenses', [])
                skus = [lic.get('skuId') for lic in assigned if lic.get('skuId')]
                logger.debug("Found assigned license skus: %s", skus)
                return skus
            except Exception:
                logger.exception("Error parsing assigned licenses response")
                return []
        else:
            logger.error("Could not fetch assigned licenses: %s", getattr(resp, 'status_code', None))
            return []

    async def _remove_licenses(self, headers, user_id: str) -> bool:
        skus = await self._get_assigned_license_skus(headers, user_id)
        if not skus:
            logger.debug("No licenses to remove for %s", user_id)
            return True

        payload = json.dumps({"addLicenses": [], "removeLicenses": skus})
        url = f"{settings.MS_API_URL}/users/{user_id}/assignLicense"
        resp = requests.post(url, headers=headers, data=payload)
        if resp.status_code in (200, 204):
            logger.debug("Removed licenses for %s", user_id)
            return True
        # Graph sometimes returns 200 with error details in body; be permissive but log
        logger.error("License removal returned %s for %s", getattr(resp, 'status_code', None), user_id)
        try:
            logger.debug(resp.json())
        except Exception:
            pass
        return False

    async def _remove_from_groups(self, headers, user_id: str) -> bool:
        # List direct groups
        url = f"{settings.MS_API_URL}/users/{user_id}/memberOf"
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            logger.error("Failed to list groups for %s: %s", user_id, getattr(resp, 'status_code', None))
            return False

        items = resp.json().get('value', [])
        success = True
        for item in items:
            # Only remove from actual groups (not directoryRoles etc)
            otype = item.get('@odata.type', '')
            if 'group' not in otype.lower():
                continue
            group_id = item.get('id')
            if not group_id:
                continue
            del_url = f"{settings.MS_API_URL}/groups/{group_id}/members/{user_id}/$ref"
            dresp = requests.delete(del_url, headers=headers)
            if dresp.status_code in (204, 200):
                logger.debug("Removed user %s from group %s", user_id, group_id)
            else:
                logger.error("Failed to remove user %s from group %s: %s", user_id, group_id, getattr(dresp, 'status_code', None))
                success = False

        return success

    async def _find_departed_site_drive(self, headers) -> Optional[dict]:
        """Locate the SharePoint site/drive for 'Departed Users'.

        This is a best-effort search that looks for a site whose displayName
        or name includes 'Departed Users'. Returns a dict with siteId and driveId
        or None if not found.
        """
        # Try Graph search for sites
        search_url = f"{settings.MS_API_URL}/sites"
        params = {'search': 'Departed Users'}
        resp = requests.get(search_url, headers=headers, params=params)
        if resp.status_code != 200:
            logger.error("Failed to search sites for Departed Users: %s", getattr(resp, 'status_code', None))
            return None

        sites = resp.json().get('value', [])
        if not sites:
            logger.debug("No sites matched 'Departed Users'")
            return None

        site = sites[0]
        site_id = site.get('id')
        if not site_id:
            return None

        # Get drive for site
        drive_url = f"{settings.MS_API_URL}/sites/{site_id}/drive"
        dresp = requests.get(drive_url, headers=headers)
        if dresp.status_code != 200:
            logger.error("Failed to get drive for site %s: %s", site_id, getattr(dresp, 'status_code', None))
            return None

        drive = dresp.json()
        return {'siteId': site_id, 'driveId': drive.get('id'), 'rootId': drive.get('root', {}).get('id')}

    async def _copy_onedrive_to_sharepoint(self, headers, user_id: str) -> bool:
        """Copy top-level items in the user's OneDrive root to the Departed Users SharePoint drive.

        NOTE: This implements copying only the immediate children of root. Recursing through
        nested folders or handling very large drives requires additional work (paging and polling).
        """
        target = await self._find_departed_site_drive(headers)
        if not target:
            logger.error("No Departed Users drive found; skipping OneDrive copy")
            return False

        # List root children
        list_url = f"{settings.MS_API_URL}/users/{user_id}/drive/root/children"
        resp = requests.get(list_url, headers=headers)
        if resp.status_code != 200:
            logger.error("Failed to list OneDrive items for %s: %s", user_id, getattr(resp, 'status_code', None))
            return False

        items = resp.json().get('value', [])
        if not items:
            logger.debug("No OneDrive items found for %s", user_id)
            return True

        success = True
        for item in items:
            item_id = item.get('id')
            name = item.get('name')
            if not item_id:
                continue

            copy_url = f"{settings.MS_API_URL}/users/{user_id}/drive/items/{item_id}/copy"
            payload = {
                "parentReference": {
                    "driveId": target['driveId'],
                    "id": target['rootId']
                },
                "name": name
            }
            cresp = requests.post(copy_url, headers=headers, data=json.dumps(payload))
            if cresp.status_code in (202, 201, 200):
                logger.debug("Requested copy of %s to Departed Users", name)
            else:
                logger.error("Failed to initiate copy for %s: %s", name, getattr(cresp, 'status_code', None))
                success = False

        return success

    async def remove_user(self):
        """Main remove flow: locate user, disable, remove licenses, remove from groups, copy OneDrive."""
        logger.debug("Starting remove_user flow for %s", self.user.username or self.user.displayname)
        ms_token = await generate_token()
        headers = {
            "Authorization": f"Bearer {ms_token}",
            "Content-Type": "application/json"
        }

        userdata = await self._get_user(headers)
        if not userdata:
            logger.error("User not found; aborting remove flow")
            raise Exception("User not found")

        user_id = userdata.get('id')
        user_response = UserResponse(
            username=userdata.get('userPrincipalName', ''),
            email=userdata.get('mail', ''),
            user_id=user_id,
            displayname=userdata.get('displayName', ''),
            message="Remove flow started"
        )

        # Disable account
        if await self._disable_account(headers, user_id):
            user_response.message += ". Account disabled"
        else:
            user_response.message += ". Failed to disable account"

        # Remove licenses
        if await self._remove_licenses(headers, user_id):
            user_response.message += ". Licenses removed"
        else:
            user_response.message += ". License removal encountered errors"

        # Remove from groups
        if await self._remove_from_groups(headers, user_id):
            user_response.message += ". Removed from groups"
        else:
            user_response.message += ". Some groups could not be removed"

        # Copy OneDrive files to Departed Users SharePoint
        if await self._copy_onedrive_to_sharepoint(headers, user_id):
            user_response.message += ". OneDrive copy requested"
        else:
            user_response.message += ". OneDrive copy failed or skipped"

        # Notify via Slack
        try:
            send_slack(user_response)
        except Exception:
            logger.exception("Failed to send slack for remove flow")

        logger.info("Remove flow finished for %s", user_response.username)
        return user_response
