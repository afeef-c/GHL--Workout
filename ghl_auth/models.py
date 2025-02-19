from django.db import models
from django.utils.timezone import now
from datetime import timedelta
import requests
from django.conf import settings

class GHLOAuth(models.Model):
    location_id = models.CharField(max_length=255, unique=True)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField()

    def __str__(self):
        return self.location_id


    def is_expired(self):
        return now() >= self.expires_at

    def refresh_access_token(self):
        if not self.refresh_token:
            return None  
        
        url = "https://services.leadconnectorhq.com/oauth/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": settings.GHL_CLIENT_ID,
            "client_secret": settings.GHL_CLIENT_SECRET
        }

        response = requests.post(url, data=data)

        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.refresh_token = token_data.get("refresh_token", self.refresh_token)  # Keep old if not provided
            self.expires_at = now() + timedelta(seconds=token_data["expires_in"])
            self.save()
            return self.access_token
        else:
            print("Failed to refresh token:", response.json())
            return None

    def get_valid_access_token(self):
        """Get a valid access token, refreshing if expired."""
        if self.is_expired():
            return self.refresh_access_token()
        return self.access_token



# class Contact(models.Model):
#     contact_id = models.CharField(max_length=255, unique=True)  
#     first_name = models.CharField(max_length=255, blank=True, null=True)
#     last_name = models.CharField(max_length=255, blank=True, null=True)
#     email = models.EmailField(blank=True, null=True)
#     assignedTo = models.CharField(max_length=255, blank=True, null=True)
#     phone = models.CharField(max_length=20, blank=True, null=True)
#     location_id = models.CharField(max_length=255)  
#     country = models.CharField(max_length=10)
#     source = models.CharField(max_length=255)
    
#     Twitter = models.TextField(null=True, blank=True)
#     Instagram = models.TextField(null=True, blank=True)
#     EmailHost = models.TextField(null=True, blank=True)
#     MainCategory = models.TextField(null=True, blank=True)
#     Google_Rank = models.TextField(null=True, blank=True)
    
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now_add=True)
    



class Contact(models.Model):
    contact_id = models.CharField(max_length=255, unique=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    location_id = models.CharField(max_length=255)
    opportunity = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 

    class Meta:
        db_table = "Contact"  


class Opportunity(models.Model):
    opportunity_id = models.CharField(max_length=255, unique=True)  
    contact_id = models.CharField(max_length=255)  
    name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    location_id = models.CharField(max_length=255)  
    monetaryValue = models.FloatField(blank=True, null=True,default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  

    class Meta:
        db_table = "Opportunity" 

    
