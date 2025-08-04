from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import gettext_lazy as _

from spodcat.model_mixin import ModelMixin
from spodcat.models.functions import (
    season_image_storage,
    season_image_thumbnail_storage,
    season_image_thumbnail_upload_to,
    season_image_upload_to,
)
from spodcat.utils import delete_storage_file, generate_thumbnail


if TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import RelatedManager

    from .episode import Episode
    from .podcast import Podcast


class Season(ModelMixin, models.Model):
    podcast = models.ForeignKey["Podcast"](
        "spodcat.Podcast",
        on_delete=models.PROTECT,
        related_name="seasons",
        verbose_name=_("podcast"),
    )
    number = models.PositiveSmallIntegerField(verbose_name=_("number"))
    name = models.CharField(max_length=100, verbose_name=_("name"), null=True, blank=True, default=None)
    image = models.ImageField(
        null=True,
        default=None,
        blank=True,
        upload_to=season_image_upload_to,
        storage=season_image_storage,
        verbose_name=_("image"),
        max_length=300,
    )
    image_height = models.PositiveIntegerField(null=True, default=None)
    image_mimetype = models.CharField(max_length=50, null=True, default=None)
    image_thumbnail = models.ImageField(
        null=True,
        default=None,
        blank=True,
        upload_to=season_image_thumbnail_upload_to,
        storage=season_image_thumbnail_storage,
        max_length=300,
    )
    image_thumbnail_height = models.PositiveIntegerField(null=True, default=None)
    image_thumbnail_mimetype = models.CharField(max_length=50, null=True, default=None)
    image_thumbnail_width = models.PositiveIntegerField(null=True, default=None)
    image_width = models.PositiveIntegerField(null=True, default=None)

    episodes: "RelatedManager[Episode]"

    class Meta:
        verbose_name = _("season")
        verbose_name_plural = _("seasons")

    def __str__(self) -> str:
        if self.name:
            return f"{self.number}: {self.name}"
        return str(self.number)

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
