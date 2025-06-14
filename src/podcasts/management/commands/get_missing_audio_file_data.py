from django.core.management import BaseCommand
from django.db.models import Q

from podcasts.models.episode import Episode


class Command(BaseCommand):
    def handle(self, *args, **options):
        episodes = list(
            Episode.objects
            .exclude(Q(audio_file="") | Q(audio_file=None))
            .filter(Q(dbfs_array=[]) | Q(duration_seconds=0))
        )
        self.stdout.write(f"Found {len(episodes)} episodes in need of updating.")
        for episode in episodes:
            self.stdout.write(f"Getting dBFS and duration data for {episode} ...")
            episode.get_dbfs_and_duration()
