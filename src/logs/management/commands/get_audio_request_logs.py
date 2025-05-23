from django.core.management import BaseCommand

from logs.utils import create_audio_request_logs
from podcasts.models import Podcast


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--environment", "-e", type=str)
        parser.add_argument("--complete", action="store_true")
        parser.add_argument("--no-bots", action="store_true")
        parser.add_argument("podcasts", nargs="*")

    def handle(self, *args, **options):
        podcasts = Podcast.objects.all()
        if options["podcasts"]:
            podcasts = podcasts.filter(slug__in=options["podcasts"])

        for podcast in podcasts:
            self.stdout.write(f"Getting new audio request logs for {podcast} ...")
            for log in create_audio_request_logs(
                podcast_slug=podcast.slug,
                environment=options["environment"],
                complete=options["complete"],
                no_bots=options["no_bots"],
            ):
                created = log.created.strftime("%Y-%m-%d %H:%M:%S")
                self.stdout.write(f"{created}\t{log.remote_addr}\t{log.episode}")
