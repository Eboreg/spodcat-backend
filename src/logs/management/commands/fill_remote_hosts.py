from django.core.management import BaseCommand

from logs.models import RequestLog


class Command(BaseCommand):
    def handle(self, *args, **options):
        RequestLog.fill_remote_hosts()
