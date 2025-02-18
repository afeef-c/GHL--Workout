from django.contrib import admin
from .models import GHLOAuth,Contact,Opportunity
from django_celery_beat.models import PeriodicTask, IntervalSchedule


admin.site.register(GHLOAuth)
admin.site.register(Contact)
admin.site.register(Opportunity)
# admin.site.register(PeriodicTask)
# admin.site.register(IntervalSchedule)