import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ghl_demo.settings')

app = Celery('ghl_demo')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "fetch-contact-every-hour": {
        "task": "ghl_auth.tasks.fetch_contacts_task",
        "schedule": crontab(minute=0, hour='*/1'),
    },
    "fetch-opportunities-every-hour": {
        "task": "ghl_auth.tasks.fetch_opportunities_task",
        "schedule": crontab(minute=0, hour='*/1'),
    },
    "update-contact-opportunity-totals-every-hour": {  # Corrected key
        "task": "ghl_auth.tasks.update_contact_opportunity_totals",
        "schedule": crontab(minute=0, hour='*/1'),
    },
}

app.conf.timezone = "UTC"
