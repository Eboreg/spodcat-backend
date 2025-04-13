from django.core.management import BaseCommand
from logs.utils import get_audio_request_logs
from podcasts.models.podcast import Podcast


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--environment", "-e", type=str)

    def handle(self, *args, **options):
        for podcast in Podcast.objects.all():
            self.stdout.write(f"Getting new audio request logs for {podcast} ...")
            logs = get_audio_request_logs(podcast=podcast, environment=options["environment"])
            self.stdout.write(f"{len(logs)} new logs imported.")
