from celery import shared_task
from django.core.management import call_command

@shared_task
def generer_loyers_task():
    call_command("generer_loyers")
