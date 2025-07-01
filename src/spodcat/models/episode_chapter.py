from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import gettext_lazy as _

from spodcat.types import ChapterDict
from spodcat.utils import filter_values_not_null
from spodcat.utils.model_fields import TimestampField
from spodcat.utils.model_mixin import ModelMixin

from .functions import episode_chapter_image_path


if TYPE_CHECKING:
    from .episode import Episode


class AbstractEpisodeChapter(ModelMixin, models.Model):
    title = models.CharField(max_length=100, blank=True, default="", verbose_name=_("title"))
    start_time = TimestampField(verbose_name=_("start time"))
    end_time = TimestampField(null=True, default=None, blank=True, verbose_name=_("end time"))
    image = models.ImageField(
        null=True,
        default=None,
        blank=True,
        upload_to=episode_chapter_image_path,
        verbose_name=_("image"),
    )
    url = models.URLField(null=True, default=None, blank=True, verbose_name=_("URL"))

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
    episode: "Episode" = models.ForeignKey(
        "spodcat.Episode",
        on_delete=models.CASCADE,
        related_name="chapters",
        verbose_name=_("episode"),
    )

    class Meta:
        verbose_name = _("episode chapter")
        verbose_name_plural = _("episode chapters")
