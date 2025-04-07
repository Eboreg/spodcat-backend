import datetime
import logging
import mimetypes
import tempfile
from io import BytesIO
from time import struct_time
from typing import IO, TYPE_CHECKING, Self
from urllib.parse import urljoin

import feedparser
import requests
from django.conf import settings
from django.core.files import File
from django.core.files.images import ImageFile
from django.db import models
from django.urls import reverse
from klaatu_python.utils import getitem0_nullable
from markdownify import markdownify
from pydub.utils import mediainfo
from slugify import slugify

from podcasts.models.fields import ImageField
from podcasts.models.podcast_content import PodcastContent
from podcasts.utils import (
    delete_storage_file,
    generate_thumbnail,
    get_audio_file_dbfs_array,
)


if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager

    from podcasts.models import EpisodeSong, Podcast


logger = logging.getLogger(__name__)


def episode_audio_file_path(instance: "Episode", filename: str):
    return f"{instance.podcast.slug}/episodes/{filename}"


def episode_image_path(instance: "Episode", filename: str):
    return f"{instance.podcast.slug}/images/{filename}"


class Episode(PodcastContent):
    season = models.PositiveSmallIntegerField(null=True, default=None, blank=True)
    number = models.PositiveSmallIntegerField(null=True, default=None, blank=True)
    audio_file = models.FileField(upload_to=episode_audio_file_path, null=True, default=None, blank=True)
    duration_seconds = models.FloatField(blank=True, verbose_name="duration", default=0.0)
    dbfs_array = models.JSONField(blank=True, default=list)
    audio_content_type = models.CharField(max_length=100, blank=True)
    audio_file_length = models.PositiveIntegerField(blank=True, default=0)
    image = ImageField(null=True, default=None, blank=True, upload_to=episode_image_path)
    image_height = models.PositiveIntegerField(null=True, default=None)
    image_width = models.PositiveIntegerField(null=True, default=None)
    image_mimetype = models.CharField(max_length=50, null=True, default=None)
    image_thumbnail = ImageField(null=True, default=None, blank=True, upload_to=episode_image_path)
    image_thumbnail_height = models.PositiveIntegerField(null=True, default=None)
    image_thumbnail_width = models.PositiveIntegerField(null=True, default=None)
    image_thumbnail_mimetype = models.CharField(max_length=50, null=True, default=None)

    songs: "RelatedManager[EpisodeSong]"
    objects: models.Manager[Self]

    @property
    def audio_url(self):
        return urljoin(settings.ROOT_URL, reverse("episode-audio", args=(self.slug,)))

    def __str__(self):
        if self.number is not None:
            return f"{self.number}. {self.name}"
        return self.name

    def update_from_feed(self, entry: feedparser.FeedParserDict):
        try:
            self.number = int(entry.itunes_episode)
        except Exception:
            pass

        try:
            self.season = int(entry.itunes_season)
        except Exception:
            pass

        self.name = markdownify(entry.title)

        if "description" in entry:
            self.description = markdownify(entry.description)

        if "published_parsed" in entry and isinstance(entry.published_parsed, struct_time):
            self.published = datetime.datetime(
                year=entry.published_parsed.tm_year,
                month=entry.published_parsed.tm_mon,
                day=entry.published_parsed.tm_mday,
                hour=entry.published_parsed.tm_hour,
                minute=entry.published_parsed.tm_min,
                second=entry.published_parsed.tm_sec,
                tzinfo=datetime.timezone.utc,
            )

        if "itunes_duration" in entry and entry.itunes_duration:
            if isinstance(entry.itunes_duration, str) and ":" in entry.itunes_duration:
                parts = entry.itunes_duration.split(":")
                duration_seconds = float(parts[-1])
                if len(parts) > 1:
                    duration_seconds += float(parts[-2]) * 60
                if len(parts) > 2:
                    duration_seconds += float(parts[-3]) * 60 * 60
                self.duration_seconds = duration_seconds
            else:
                try:
                    self.duration_seconds = float(entry.itunes_duration)
                except ValueError:
                    pass

        if "image" in entry and "href" in entry.image and entry.image.href:
            logger.info("Importing episode image: %s", entry.image.href)
            response = requests.get(entry.image.href, timeout=10)
            if response.ok:
                suffix = ""
                content_type = response.headers.get("Content-Type", "")
                if content_type:
                    suffix = mimetypes.guess_extension(content_type) or ("." + content_type.split("/")[-1])
                delete_storage_file(self.image)
                # pylint: disable=no-member
                self.image.save(
                    name=f"{self.generate_filename_stem()}{suffix}",
                    content=ImageFile(file=BytesIO(response.content)),
                    save=False,
                )
                self.handle_uploaded_image()

        if "links" in entry:
            link = getitem0_nullable(entry.links, lambda l: l.get("rel", "") == "enclosure")
            if link and "href" in link:
                logger.info("Fetching audio file: %s", link.href)
                response = requests.get(link.href, timeout=60)
                if response.ok:
                    delete_storage_file(self.audio_file)
                    self.audio_content_type = response.headers.get("Content-Type", "")
                    prefix, suffix = self.generate_audio_filename()
                    filename = f"{prefix}{suffix}"

                    with tempfile.NamedTemporaryFile(suffix=suffix) as file:
                        logger.info("Saving audio file: %s", filename)
                        file.write(response.content)
                        # pylint: disable=no-member
                        self.audio_file.save(name=filename, content=File(file=file), save=False)
                        info = mediainfo(file.name)
                        self.duration_seconds = float(info["duration"])
                        self.audio_file_length = len(response.content)
                        file.seek(0)
                        logger.info("Updating dBFS array for audio file")
                        self.update_audio_file_dbfs_array(file=file, format_name=info["format_name"], save=False)

        self.save()

    # pylint: disable=no-member
    def handle_uploaded_image(self, save: bool = False):
        delete_storage_file(self.image_thumbnail)
        if self.image:
            mimetype = generate_thumbnail(self.image, self.image_thumbnail, 150, save)
            self.image_mimetype = mimetype
            self.image_thumbnail_mimetype = mimetype
            self.image_height = self.image.height
            self.image_width = self.image.width
            self.image_thumbnail_height = self.image_thumbnail.height
            self.image_thumbnail_width = self.image_thumbnail.width
        else:
            self.image_mimetype = None
            self.image_thumbnail_mimetype = None
            self.image_height = None
            self.image_width = None
            self.image_thumbnail_height = None
            self.image_thumbnail_width = None
        if save:
            self.save()

    @classmethod
    def from_feed(
        cls,
        entry: feedparser.FeedParserDict,
        podcast: "Podcast",
        update: bool = False,
    ) -> Self:
        episode: Self | None = None
        try:
            number = int(entry.itunes_episode)
        except Exception:
            number = None

        if number is not None:
            episode = cls.objects.filter(podcast=podcast, number=number).first()
            if episode:
                if not update:
                    logger.info("Episode %d already exists and update=False - skipping", number)
                    return episode
                logger.info("Episode %d already exists and update=True - updating", number)

        if not episode:
            logger.info("Creating episode: %s", entry.title)
            episode = cls(podcast=podcast, number=number)

        episode.name = entry.title

        if "description" in entry:
            episode.description = entry.description

        if "published_parsed" in entry and isinstance(entry.published_parsed, struct_time):
            episode.published = datetime.datetime(
                year=entry.published_parsed.tm_year,
                month=entry.published_parsed.tm_mon,
                day=entry.published_parsed.tm_mday,
                hour=entry.published_parsed.tm_hour,
                minute=entry.published_parsed.tm_min,
                second=entry.published_parsed.tm_sec,
                tzinfo=datetime.timezone.utc,
            )

        if "itunes_duration" in entry and entry.itunes_duration:
            if isinstance(entry.itunes_duration, str) and ":" in entry.itunes_duration:
                parts = entry.itunes_duration.split(":")
                duration_seconds = float(parts[-1])
                if len(parts) > 1:
                    duration_seconds += float(parts[-2]) * 60
                if len(parts) > 2:
                    duration_seconds += float(parts[-3]) * 60 * 60
                episode.duration_seconds = duration_seconds
            else:
                try:
                    episode.duration_seconds = float(entry.itunes_duration)
                except ValueError:
                    pass

        if "links" in entry:
            link = getitem0_nullable(entry.links, lambda l: l.get("rel", "") == "enclosure")
            if link and "href" in link:
                logger.info("Fetching audio file: %s", link.href)
                response = requests.get(link.href, timeout=60)
                if response.ok:
                    episode.audio_content_type = response.headers.get("Content-Type", "")
                    prefix, suffix = episode.generate_audio_filename()
                    filename = f"{prefix}{suffix}"

                    with tempfile.NamedTemporaryFile(suffix=suffix) as file:
                        logger.info("Saving audio file: %s", filename)
                        file.write(response.content)
                        episode.audio_file.save(name=filename, content=File(file=file), save=False)
                        info = mediainfo(file.name)
                        episode.duration_seconds = float(info["duration"])
                        episode.audio_file_length = len(response.content)
                        file.seek(0)
                        logger.info("Updating dBFS array for audio file")
                        episode.update_audio_file_dbfs_array(file=file, format_name=info["format_name"], save=False)

        episode.save()
        return episode

    def _get_base_slug(self) -> str:
        base_slug = slugify(self.name)
        if self.number is not None:
            base_slug = f"{self.number}-" + base_slug
        return base_slug

    def generate_audio_filename(self) -> tuple[str, str]:
        suffix = mimetypes.guess_extension(self.audio_content_type)
        if not suffix:
            if self.audio_content_type:
                suffix = "." + self.audio_content_type.split("/")[-1]
            else:
                suffix = ""
        assert suffix is not None
        return self.generate_filename_stem(), suffix

    def generate_filename_stem(self) -> str:
        numbers = []
        name = ""

        if self.season is not None:
            numbers.append(f"S{self.season:02d}")
        if self.number is not None:
            numbers.append(f"E{self.number:02d}")
        if numbers:
            name += "".join(numbers) + "-"
        name += slugify(self.name, max_length=50)

        return name

    def update_audio_file_dbfs_array(self, file: IO, format_name: str, save: bool = True):
        self.dbfs_array = get_audio_file_dbfs_array(file, format_name)

        if save:
            self.save()
