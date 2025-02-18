import logging
import requests
from celery import shared_task
from django.db import transaction
from django.http import JsonResponse
from .models import GHLOAuth, Contact,Opportunity
from .utils import convert_to_timezone, get_custom_field_name  # Utility functions
from datetime import datetime
from django.db import connection, transaction

import time

contact_logger = logging.getLogger(__name__)




@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def fetch_contacts_task(self, location_id=None):
    try:
        contact_logger.info("Task started.")
        
        location_ids = [location_id] if location_id else list(GHLOAuth.objects.values_list("location_id", flat=True))
        
        if not location_ids:
            contact_logger.error("No locations found in the database.")
            return {"error": "No locations found"}

        for loc_id in location_ids:
            contact_logger.info(f"Processing location_id: {loc_id}")
            
            oauth_entry = GHLOAuth.objects.filter(location_id=loc_id).first()
            if not oauth_entry:
                contact_logger.error(f"No stored token for location {loc_id}")
                continue

            access_token = oauth_entry.get_valid_access_token()
            if not access_token:
                contact_logger.error(f"Failed to retrieve access token for {loc_id}")
                continue

            url = "https://services.leadconnectorhq.com/contacts/search"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Version": "2021-07-28",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            contacts_to_store = []
            contacts_to_update = []
            existing_contacts = {
                contact.contact_id: contact for contact in Contact.objects.filter(location_id=loc_id)
            }
            
            page_limit = 100  # Increased page limit to reduce API calls
            search_after = None
            batch_size = 3000
            
            while True:
                payload = {"locationId": loc_id, "pageLimit": page_limit}
                if search_after:
                    payload["searchAfter"] = search_after
                
                response = requests.post(url, json=payload, headers=headers)
                
                if response.status_code != 200:
                    contact_logger.error(f"Failed to fetch contacts for {loc_id}. Status: {response.status_code}, Response: {response.text}")
                    break  # Stop processing this location
                
                try:
                    data = response.json()
                except ValueError as e:
                    contact_logger.error(f"Invalid JSON response for location {loc_id}: {str(e)}")
                    break
                
                contacts_data = data.get("contacts", [])
                contact_logger.info(f"Contacts received for {loc_id}: {len(contacts_data)}")
                
                if not contacts_data:
                    break  # Stop if no more contacts
                
                for contact in contacts_data:
                    contact_id = contact.get("id")
                    added_at_utc = contact.get("dateAdded")
                    updated_at_utc = contact.get("dateUpdated")
                    added_at_local = convert_to_timezone(added_at_utc, "Asia/Kolkata") if added_at_utc else None
                    updated_at_local = convert_to_timezone(updated_at_utc, "Asia/Kolkata") if updated_at_utc else None
                    
                    if contact_id in existing_contacts:
                        existing_contact = existing_contacts[contact_id]
                        existing_contact.first_name = (contact.get("firstNameLowerCase") or "").title()
                        existing_contact.last_name = (contact.get("lastNameLowerCase") or "").title()
                        existing_contact.email = contact.get("email")
                        existing_contact.phone = contact.get("phone")
                        existing_contact.created_at = added_at_local
                        existing_contact.updated_at = updated_at_local
                        contacts_to_update.append(existing_contact)
                    else:
                        contacts_to_store.append(Contact(
                            contact_id=contact_id,
                            location_id=loc_id,
                            first_name=(contact.get("firstNameLowerCase") or "").title(),
                            last_name=(contact.get("lastNameLowerCase") or "").title(),
                            email=contact.get("email"),
                            phone=contact.get("phone"),
                            created_at=added_at_local,
                            updated_at=updated_at_local
                        ))
                
                contact_logger.info(f"New contacts to insert: {len(contacts_to_store)}, Existing contacts to update: {len(contacts_to_update)}")
                
                if contacts_to_update:
                    with transaction.atomic():
                        Contact.objects.bulk_update(
                            contacts_to_update,
                            ["first_name", "last_name", "email", "phone", "created_at", "updated_at"]
                        )
                    contact_logger.info(f"Updated {len(contacts_to_update)} contacts in DB.")
                    contacts_to_update = []
                    
                
                if len(contacts_to_store) >= batch_size:
                    with transaction.atomic():
                        Contact.objects.bulk_create(contacts_to_store, ignore_conflicts=True)
                    contact_logger.info(f"Stored {len(contacts_to_store)} new contacts in DB.")
                    contacts_to_store = []
                
                search_after = contacts_data[-1].get("searchAfter") if contacts_data else None
                if not search_after:
                    break
            
            if contacts_to_store:
                with transaction.atomic():
                    Contact.objects.bulk_create(contacts_to_store, ignore_conflicts=True)
                contact_logger.info(f"Stored remaining {len(contacts_to_store)} new contacts in DB.")
            
            if contacts_to_update:
                with transaction.atomic():
                    Contact.objects.bulk_update(
                        contacts_to_update,
                        ["first_name", "last_name", "email", "phone", "created_at", "updated_at"]
                    )
                contact_logger.info(f"Updated remaining {len(contacts_to_update)} contacts in DB.")
        
        contact_logger.info("Task completed successfully.")
        return {"message": "Contacts fetched, updated, and stored successfully"}
    
    except Exception as e:
        contact_logger.exception(f"Unexpected error: {str(e)}")
        raise self.retry(exc=e)  # Retry the task in case of failure




logger = logging.getLogger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def fetch_opportunities_task(self, location_id=None):
    try:
        location_ids = [location_id] if location_id else list(GHLOAuth.objects.values_list("location_id", flat=True))
        
        if not location_ids:
            logger.error("No locations found in the database.")
            return {"error": "No locations found"}

        for loc_id in location_ids:
            logger.info(f"Processing location_id: {loc_id}")
            
            oauth_entry = GHLOAuth.objects.filter(location_id=loc_id).first()
            if not oauth_entry:
                logger.error(f"No stored token for location {loc_id}")
                continue

            access_token = oauth_entry.get_valid_access_token()
            if not access_token:
                logger.error(f"Failed to retrieve access token for {loc_id}")
                continue

            url = f"https://services.leadconnectorhq.com/opportunities/search?location_id={loc_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Version": "2021-07-28",
                "Accept": "application/json"
            }

            page_limit = 100  # API limit
            start_after = None
            start_after_id = None
            opportunities_to_store = []
            opportunities_update = []
            batch_size = 3000

            existing_opportunities = {
                opp.opportunity_id: opp for opp in Opportunity.objects.filter(location_id=loc_id)
            }

            while True:
                params = {"limit": page_limit}
                if start_after:
                    params["startAfter"] = start_after
                    params["startAfterId"] = start_after_id

                retry_attempts = 3
                while retry_attempts > 0:
                    response = requests.get(url, headers=headers, params=params)
                    logger.info(f"Response status code: {response.status_code}")

                    if response.status_code == 520:
                        logger.error("520 Error encountered. Retrying...")
                        retry_attempts -= 1
                        time.sleep(5)  # Wait before retrying
                    else:
                        break

                if response.status_code != 200:
                    logger.error(f"Failed to fetch opportunities for {loc_id}. Status: {response.status_code}, Response: {response.text}")
                    break

                try:
                    data = response.json()
                except ValueError as e:
                    logger.error(f"Invalid JSON response for location {loc_id}: {str(e)}")
                    break

                opportunities_data = data.get("opportunities", [])
                meta_data = data.get("meta", {})
                logger.info(f"Opportunities received for {loc_id}: {len(opportunities_data)} total-oppr to update {len(opportunities_to_store)}")

                if not opportunities_data:
                    break

                for opportunity in opportunities_data:
                    opportunity_id = opportunity.get("id")
                    contact_id = opportunity.get("contactId")
                    name = opportunity.get("name")
                    phone = opportunity.get("phone")
                    monetary_value = opportunity.get("monetaryValue")

                    if opportunity_id in existing_opportunities:
                        existing_opportunity = existing_opportunities[opportunity_id]
                        existing_opportunity.name = name
                        existing_opportunity.phone = phone
                        existing_opportunity.monetaryValue = monetary_value
                        opportunities_update.append(existing_opportunity)
                    else:
                        opportunities_to_store.append(Opportunity(
                            opportunity_id=opportunity_id,
                            contact_id=contact_id,
                            name=name,
                            phone=phone,
                            location_id=loc_id,
                            monetaryValue=monetary_value
                        ))

                # Bulk update existing opportunities
                if opportunities_update:
                    with transaction.atomic():
                        Opportunity.objects.bulk_update(
                            opportunities_update, ["name", "phone", "monetaryValue"]
                        )
                    logger.info(f"Updated {len(opportunities_update)} opportunities in DB.")
                    opportunities_update = []  # Clear after update

                # Bulk insert new opportunities
                if len(opportunities_to_store) >= batch_size:
                    with transaction.atomic():
                        Opportunity.objects.bulk_create(opportunities_to_store, ignore_conflicts=True)
                    logger.info(f"Stored {len(opportunities_to_store)} new opportunities in DB.")
                    opportunities_to_store = []  # Clear after insert

                start_after = meta_data.get("startAfter") if meta_data else None
                start_after_id = meta_data.get("startAfterId") if meta_data else None
                logger.info(f"start_after and  start_after_id: {start_after} - {start_after_id}")

                if not start_after or not start_after_id:
                    break

            if opportunities_to_store:
                with transaction.atomic():
                    Opportunity.objects.bulk_create(opportunities_to_store, ignore_conflicts=True)
                logger.info(f"Stored {len(opportunities_to_store)} new opportunities in DB.")

        update_contact_opportunity_totals.delay()
        logger.info("Task completed successfully.")
        return {"message": "Opportunities fetched and stored successfully"}

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise self.retry(exc=e)  # Retry the task in case of failure





@shared_task(bind=True)
def update_contact_opportunity_totals(self):
    try:
        cursor = connection.cursor()

        contact_logger.info("Updating contact opportunity totals...")

        cursor.execute(
            """
            UPDATE Contact
            SET opportunity = (
                SELECT COALESCE(SUM(monetaryValue), 0)
                FROM Opportunity
                WHERE Opportunity.contact_id = Contact.contact_id
            )
            WHERE EXISTS (
                SELECT 1 FROM Opportunity WHERE Opportunity.contact_id = Contact.contact_id
            );
            """
        )

        contact_logger.info("Contact opportunity totals updated successfully.")
        return {"message": "Contact opportunity totals updated"}

    except Exception as e:
        contact_logger.exception(f"Unexpected error: {str(e)}")
        return {"error": str(e)}

