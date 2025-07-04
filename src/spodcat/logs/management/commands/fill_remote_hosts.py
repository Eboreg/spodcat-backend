from django.core.management import BaseCommand

from spodcat.logs.models import (
    PodcastContentRequestLog,
    PodcastEpisodeAudioRequestLog,
    PodcastRequestLog,
    PodcastRssRequestLog,
)


class Command(BaseCommand):
    def handle(self, *args, **options):
        PodcastRequestLog.fill_remote_hosts()
        PodcastContentRequestLog.fill_remote_hosts()
        PodcastEpisodeAudioRequestLog.fill_remote_hosts()
        PodcastRssRequestLog.fill_remote_hosts()
