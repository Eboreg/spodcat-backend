from datetime import timedelta

from django.core.management import BaseCommand
from django.utils import timezone

from spodcat.models import Challenge


class Command(BaseCommand):
    def handle(self, *args, **options):
        deleted = Challenge.objects.filter(created__lt=timezone.now() - timedelta(days=7)).delete()
        self.stdout.write(f"{deleted[0]} old challenge(s) deleted.")
