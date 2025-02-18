from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('start-oauth/', views.start_ghl_oauth, name='start-oauth'),
    path('oauth/callback/', views.ghl_callback, name='ghl-callback'),
    path('exchange-token/', views.exchange_code_for_token, name='exchange_code_for_token'),
    path('fetch-contacts/<str:location_id>/', views.fetch_contacts, name='fetch_contacts'),

    

]