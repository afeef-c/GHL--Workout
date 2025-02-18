from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json

class Command(BaseCommand):
    help = "Setup periodic Celery tasks"

    def handle(self, *args, **kwargs):
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=30,  
            period=IntervalSchedule.SECONDS
        )

        task_name = "print_hello_task"
        if not PeriodicTask.objects.filter(name=task_name).exists():
            PeriodicTask.objects.create(
                interval=schedule,
                name=task_name,
                task="ghl_auth.tasks.print_hello",
                args=json.dumps([]),
            )
            self.stdout.write(self.style.SUCCESS(f"Task '{task_name}' created successfully!"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Task '{task_name}' already exists."))
