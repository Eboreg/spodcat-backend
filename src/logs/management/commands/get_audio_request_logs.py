from django.core.management import BaseCommand

from logs.utils import get_audio_request_logs
from podcasts.models import Podcast


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--environment", "-e", type=str)
        parser.add_argument("--complete", action="store_true")

    def handle(self, *args, **options):
        for podcast in Podcast.objects.all():
            self.stdout.write(f"Getting new audio request logs for {podcast} ...")
            for log in get_audio_request_logs(
                podcast=podcast,
                environment=options["environment"],
                complete=options["complete"],
            ):
                created = log.created.strftime("%Y-%m-%d %H:%M:%S")
                self.stdout.write(f"{created}\t{log.remote_addr}\t{log.episode}")
