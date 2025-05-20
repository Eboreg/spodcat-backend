from typing import TYPE_CHECKING

from django.db import models

from podcasts.types import ChapterDict
from utils import filter_values_not_null
from utils.model_fields import TimestampField
from utils.model_mixin import ModelMixin


if TYPE_CHECKING:
    from podcasts.models import Episode


def episode_chapter_image_path(instance: "AbstractEpisodeChapter", filename: str):
    return f"{instance.episode.podcast.slug}/images/{filename}"


class AbstractEpisodeChapter(ModelMixin, models.Model):
    title = models.CharField(max_length=100, blank=True, default="")
    start_time = TimestampField()
    end_time = TimestampField(null=True, default=None, blank=True)
    image = models.ImageField(null=True, default=None, blank=True, upload_to=episode_chapter_image_path)
    url = models.URLField(null=True, default=None, blank=True)

    episode: "Episode"

    class Meta:
        ordering = ["start_time"]
        abstract = True

    @property
    def formatted_title(self):
        return self.title

    # pylint: disable=no-member
    def to_dict(self) -> ChapterDict:
        return filter_values_not_null({
            "endTime": self.end_time,
            "img": self.image.url if self.image else None,
            "startTime": self.start_time,
            "title": self.formatted_title,
            "url": self.url,
        })


class EpisodeChapter(AbstractEpisodeChapter):
    episode: "Episode" = models.ForeignKey("podcasts.Episode", on_delete=models.CASCADE, related_name="chapters")
