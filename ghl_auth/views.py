from datetime import timedelta,datetime
from django.shortcuts import redirect, render
from django.conf import settings
import requests
import urllib.parse
from django.utils.timezone import now
from .models import GHLOAuth,Contact
from django.http import JsonResponse
import logging
from .tasks import fetch_contacts_task,fetch_opportunities_task



def home(request):
    
    return render(request, 'home.html')

def start_ghl_oauth(request):
    auth_url = "https://marketplace.gohighlevel.com/oauth/chooselocation"
    params = {
        "response_type": "code",
        "client_id": settings.GHL_CLIENT_ID,
        "redirect_uri": 'http://127.0.0.1:8000/oauth/callback/',
        "scope": settings.SCOPE,  
    }
    auth_redirect_url = f"{auth_url}?{urllib.parse.urlencode(params)}"

    return redirect(auth_redirect_url)


def ghl_callback(request):
    code = request.GET.get('code')
    if not code:
        return JsonResponse({"error": "Missing authorization code"}, status=400)

    # Pass the code to the template for the next step
    return render(request, 'select_location.html', {'auth_code': code})


def exchange_code_for_token(request):
    if request.method == "POST":
        auth_code = request.POST.get("auth_code")
        location_id = request.POST.get("location_id")
        
        if not auth_code or not location_id:
            return JsonResponse({"error": "Missing required fields"}, status=400)

        url = "https://services.leadconnectorhq.com/oauth/token"
        
        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": settings.GHL_CLIENT_ID,
            "client_secret": settings.GHL_CLIENT_SECRET,
            "redirect_uri": settings.GHL_REDIRECT_URI
        }


        response = requests.post(url, data=data)


        
        if response.status_code == 200:
            token_data = response.json()
            print("Proper loaction id:  ", token_data['locationId'])
            if location_id == token_data['locationId']:

                # Store the token in the database
                expires_at = now() + timedelta(seconds=token_data['expires_in'])
                GHLOAuth.objects.update_or_create(
                    location_id=location_id,
                    defaults={
                        "access_token": token_data['access_token'],
                        "refresh_token": token_data.get('refresh_token', ''),
                        "expires_at": expires_at
                    }
                )

                
                return render(request, "success.html", {"message": "Access token generated and location saved!", 
                                                        "location_id":location_id,
                                                        "access_token":token_data['access_token']})

            else:
                print("response: ", response)
                return render(request, "error_page.html", {"message": "Enter correct location ID"})

        

        else:
            print("response: ", response)
            return render(request, "error_page.html", {"message": "Failed to retrieve access token"})






contact_logger = logging.getLogger(__name__)
def fetch_contacts(request, location_id):
    task1 = fetch_contacts_task.delay(location_id)
    task2 = fetch_opportunities_task.delay(location_id)
    return JsonResponse({
        "message": "Tasks started",
        "task_ids": {
            "task1_id": task1.id,
            "task2_id": task2.id
        }
    }, status=202)




