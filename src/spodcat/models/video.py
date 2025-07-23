from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import gettext_lazy as _

from spodcat.model_mixin import ModelMixin


if TYPE_CHECKING:
    from .podcast_content import PodcastContent


class Video(ModelMixin, models.Model):
    class Type(models.TextChoices):
        YOUTUBE = "youtube", _("Youtube")

    podcast_content = models.ForeignKey["PodcastContent"](
        "spodcat.PodcastContent",
        on_delete=models.CASCADE,
        related_name="videos",
        verbose_name=_("podcast content"),
    )
    video_type = models.CharField(max_length=20, choices=Type.choices, default=Type.YOUTUBE)
    video_id = models.CharField(max_length=100)
    title = models.CharField(max_length=100, null=True, blank=True, default=None, verbose_name=_("title"))
