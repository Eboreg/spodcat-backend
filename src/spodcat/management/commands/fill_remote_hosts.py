from django.core.management import BaseCommand

from spodcat.models import RequestLog


class Command(BaseCommand):
    def handle(self, *args, **options):
        RequestLog.fill_remote_hosts()
