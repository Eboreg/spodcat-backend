from django.core.management import BaseCommand
from django.utils import timezone

from podcasts.models import Challenge


class Command(BaseCommand):
    def handle(self, *args, **options):
        deleted = Challenge.objects.filter(created__lt=timezone.now() - timezone.timedelta(days=7)).delete()
        self.stdout.write(f"{deleted[0]} old challenge(s) deleted.")
