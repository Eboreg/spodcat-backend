from django.core.management import BaseCommand

from spodcat.logs.models import (
    PodcastContentRequestLog,
    PodcastEpisodeAudioRequestLog,
    PodcastRequestLog,
    PodcastRssRequestLog,
)


class Command(BaseCommand):
    def handle(self, *args, **options):
        PodcastRequestLog.fill_geoips()
        PodcastContentRequestLog.fill_geoips()
        PodcastEpisodeAudioRequestLog.fill_geoips()
        PodcastRssRequestLog.fill_geoips()
