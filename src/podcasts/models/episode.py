from typing import BinaryIO
from urllib.parse import urljoin

from django.conf import settings
from django.db import models
from django.urls import reverse
from slugify import slugify

from podcasts.models.podcast_content import PodcastContent
from podcasts.utils import get_audio_file_dbfs_array


def episode_audio_file_path(instance: "Episode", filename: str):
    return f"{instance.podcast.slug}/episodes/{filename}"


class Episode(PodcastContent):
    number = models.PositiveSmallIntegerField(null=True, default=None, blank=True)
    audio_file = models.FileField(upload_to=episode_audio_file_path)
    duration_seconds = models.FloatField(blank=True, verbose_name="duration")
    dbfs_array = models.JSONField(blank=True, default=list)
    audio_content_type = models.CharField(max_length=100, blank=True)
    audio_file_length = models.PositiveIntegerField(blank=True)

    @property
    def audio_url(self):
        return urljoin(settings.ROOT_URL, reverse("episode-audio", args=(self.slug,)))

    def __str__(self):
        if self.number is not None:
            return f"{self.number}. {self.name}"
        return self.name

    def _get_base_slug(self):
        base_slug = slugify(self.name)
        if self.number is not None:
            base_slug = f"{self.number}-" + base_slug
        return base_slug

    def update_audio_file_dbfs_array(self, file: BinaryIO, format_name: str, save: bool = True):
        self.dbfs_array = get_audio_file_dbfs_array(file, format_name)

        if save:
            self.save()
