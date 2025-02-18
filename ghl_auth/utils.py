import requests
import logging
import pytz
from datetime import datetime
from django.utils.timezone import now
from django.conf import settings
from .models import GHLOAuth

def refresh_ghl_token(location_id):
    try:
        token_obj = GHLOAuth.objects.get(location_id=location_id)
        if token_obj.expires_at > now():
            return token_obj.access_token  # Token is still valid

        refresh_data = {
            "client_id": settings.GHL_CLIENT_ID,
            "client_secret": settings.GHL_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": token_obj.refresh_token,
        }

        response = requests.post("https://app.gohighlevel.com/oauth/token", data=refresh_data)
        if response.status_code != 200:
            return None

        token_info = response.json()
        token_obj.access_token = token_info["access_token"]
        token_obj.refresh_token = token_info["refresh_token"]
        token_obj.expires_at = now() + datetime.timedelta(seconds=token_info["expires_in"])
        token_obj.save()
        
        return token_obj.access_token
    except GHLOAuth.DoesNotExist:
        return None


contact_logger = logging.getLogger(__name__)


def convert_to_timezone(utc_time_str, timezone_str):
    """
    Converts UTC time string to the specified timezone.
    """
    if not utc_time_str:
        return None

    try:
        # Convert string to datetime object
        utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")

        # Set as UTC timezone
        utc_time = utc_time.replace(tzinfo=pytz.utc)

        # Convert to target timezone
        target_timezone = pytz.timezone(timezone_str)
        local_time = utc_time.astimezone(target_timezone)

        return local_time  # Returns a timezone-aware datetime object

    except ValueError:
        contact_logger.error(f"Invalid date format: {utc_time_str}")
        return None


def get_custom_field_name(location_id, field_id, access_token):
    """
    Fetch custom field name from API and store it in the database.
    """
    try:
        url = f"https://services.leadconnectorhq.com/locations/{location_id}/customFields/{field_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Version": "2021-07-28",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            field_data = response.json()
            return field_data if isinstance(field_data, dict) else {"name": "Unknown Field"}

        contact_logger.error(f"Failed to fetch custom field {field_id}, status: {response.status_code}")
        return {"name": "Unknown Field"}

    except Exception as e:
        contact_logger.error(f"Error fetching custom field {field_id}: {str(e)}")
        return {"name": "Unknown Field"}



