from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import gettext_lazy as _

from .functions import podcast_link_icon_path
from .model_mixin import ModelMixin


if TYPE_CHECKING:
    from .podcast import Podcast


class PodcastLink(ModelMixin, models.Model):
    class Icon(models.TextChoices):
        FACEBOOK = "facebook", _("The Facebook")
        PATREON = "patreon", _("Patreon")
        DISCORD = "discord", _("Discord")
        APPLE = "apple", _("Apple")
        ANDROID = "android", _("Android")
        SPOTIFY = "spotify", _("Spotify")
        ITUNES = "itunes", _("Itunes")

    class Theme(models.TextChoices):
        PRIMARY = "primary", _("Primary")
        SECONDARY = "secondary", _("Secondary")
        TERTIARY = "tertiary", _("Tertiary")
        BORING = "boring", _("Boring")

    custom_icon = models.ImageField(
        upload_to=podcast_link_icon_path,
        null=True,
        default=None,
        blank=True,
        verbose_name=_("custom icon"),
    )
    icon = models.CharField(max_length=10, choices=Icon, null=True, default=None, verbose_name=_("icon"))
    label = models.CharField(max_length=100, verbose_name=_("label"))
    order = models.PositiveSmallIntegerField(default=0, verbose_name=_("order"))
    podcast: "Podcast" = models.ForeignKey("spodcat.Podcast", on_delete=models.CASCADE, related_name="links")
    theme = models.CharField(max_length=10, choices=Theme, default=Theme.PRIMARY, verbose_name=_("theme"))
    url = models.URLField(verbose_name=_("URL"))

    class Meta:
        ordering = ["order"]
        indexes = [models.Index(fields=["order"])]
        verbose_name = _("podcast link")
        verbose_name_plural = _("podcast links")
