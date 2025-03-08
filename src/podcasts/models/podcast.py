from typing import TYPE_CHECKING
from urllib.parse import urljoin

from django.conf import settings
from django.db import models
from django.urls import reverse
from iso639 import iter_langs
from markdown import markdown
from martor.models import MartorField

from podcasts.markdown import MarkdownExtension
from podcasts.validators import podcast_cover_validator, podcast_slug_validator


if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager
    from polymorphic.managers import PolymorphicManager

    from podcasts.models import Category, Episode
    from users.models import User


def get_language_choices():
    return [(l.pt1, l.name) for l in iter_langs() if l.pt1]


def podcast_image_path(instance: "Podcast", filename: str):
    return f"{instance.slug}/images/{filename}"


class Podcast(models.Model):
    slug = models.SlugField(primary_key=True, validators=[podcast_slug_validator])
    name = models.CharField(max_length=100)
    tagline = models.CharField(max_length=500, null=True, blank=True, default=None)
    description = MartorField(null=True, default=None, blank=True)
    cover = models.ImageField(
        null=True,
        default=None,
        blank=True,
        validators=[podcast_cover_validator],
        upload_to=podcast_image_path,
        height_field="cover_height",
        width_field="cover_width",
    )
    cover_height = models.PositiveIntegerField(null=True, default=None)
    cover_width = models.PositiveIntegerField(null=True, default=None)
    cover_mimetype = models.CharField(max_length=50, null=True, default=None)
    cover_thumbnail = models.ImageField(
        null=True,
        default=None,
        blank=True,
        upload_to=podcast_image_path,
        height_field="cover_thumbnail_height",
        width_field="cover_thumbnail_width",
    )
    cover_thumbnail_height = models.PositiveIntegerField(null=True, default=None)
    cover_thumbnail_width = models.PositiveIntegerField(null=True, default=None)
    cover_thumbnail_mimetype = models.CharField(max_length=50, null=True, default=None)
    banner = models.ImageField(
        null=True,
        default=None,
        blank=True,
        upload_to=podcast_image_path,
        height_field="banner_height",
        width_field="banner_width",
    )
    banner_height = models.PositiveIntegerField(null=True, default=None)
    banner_width = models.PositiveIntegerField(null=True, default=None)
    favicon = models.ImageField(null=True, default=None, blank=True, upload_to=podcast_image_path)
    favicon_content_type = models.CharField(null=True, default=None, blank=True, max_length=50)
    owners: "RelatedManager[User]" = models.ManyToManyField("users.User", related_name="podcasts")
    language = models.CharField(max_length=5, choices=get_language_choices, null=True, blank=True, default=None)
    categories: "RelatedManager[Category]" = models.ManyToManyField("podcasts.Category")

    contents: "PolymorphicManager"

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["name"])]

    @property
    def description_html(self):
        if self.description:
            return markdown(self.description, extensions=["nl2br", "smarty", MarkdownExtension()])
        return None

    @property
    def published_episodes(self) -> "models.QuerySet[Episode]":
        from podcasts.models.episode import Episode
        return self.contents.instance_of(Episode)

    @property
    def rss_url(self):
        return urljoin(settings.ROOT_URL, reverse("podcast-rss", args=(self.slug,)))

    def __str__(self):
        return self.name
