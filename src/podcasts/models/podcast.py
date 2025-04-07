import logging
import mimetypes
from io import BytesIO
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import feedparser
import requests
from django.conf import settings
from django.core.files.images import ImageFile
from django.db import models
from django.db.models import Q
from django.urls import reverse
from iso639 import iter_langs
from markdown import markdown
from markdownify import markdownify
from martor.models import MartorField

from podcasts.markdown import MarkdownExtension
from podcasts.models.fields import ImageField
from podcasts.utils import (
    delete_storage_file,
    downscale_image,
    generate_thumbnail,
)
from podcasts.validators import podcast_cover_validator, podcast_slug_validator


if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager
    from polymorphic.managers import PolymorphicManager

    from podcasts.models import Category, PodcastLink
    from users.models import User


logger = logging.getLogger(__name__)


def get_language_choices():
    return [(l.pt1, l.name) for l in iter_langs() if l.pt1]


def podcast_image_path(instance: "Podcast", filename: str):
    return f"{instance.slug}/images/{filename}"


class Podcast(models.Model):
    slug = models.SlugField(primary_key=True, validators=[podcast_slug_validator], help_text="Will be used in URLs.")
    name = models.CharField(max_length=100)
    tagline = models.CharField(max_length=500, null=True, blank=True, default=None)
    description = MartorField(null=True, default=None, blank=True)
    cover = ImageField(
        null=True,
        default=None,
        blank=True,
        validators=[podcast_cover_validator],
        upload_to=podcast_image_path,
        height_field="cover_height",
        width_field="cover_width",
        help_text="This is the round 'avatar' image.",
    )
    cover_height = models.PositiveIntegerField(null=True, default=None)
    cover_width = models.PositiveIntegerField(null=True, default=None)
    cover_mimetype = models.CharField(max_length=50, null=True, default=None)
    cover_thumbnail = ImageField(
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
    banner = ImageField(
        null=True,
        default=None,
        blank=True,
        upload_to=podcast_image_path,
        height_field="banner_height",
        width_field="banner_width",
        verbose_name="Banner image",
        help_text="Should be >= 960px wide and have aspect ratio 3:1.",
    )
    banner_height = models.PositiveIntegerField(null=True, default=None)
    banner_width = models.PositiveIntegerField(null=True, default=None)
    favicon = ImageField(null=True, default=None, blank=True, upload_to=podcast_image_path)
    favicon_content_type = models.CharField(null=True, default=None, blank=True, max_length=50)
    owners: "RelatedManager[User]" = models.ManyToManyField("users.User", related_name="podcasts")
    language = models.CharField(max_length=5, choices=get_language_choices, null=True, blank=True, default=None)
    categories: "RelatedManager[Category]" = models.ManyToManyField("podcasts.Category", blank=True)

    contents: "PolymorphicManager"
    links: "RelatedManager[PodcastLink]"

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["name"])]

    @property
    def description_html(self):
        if self.description:
            return markdown(self.description, extensions=["nl2br", "smarty", MarkdownExtension()])
        return None

    @property
    def frontend_url(self):
        return urljoin(settings.FRONTEND_ROOT_URL, self.slug)

    @property
    def rss_url(self):
        return urljoin(settings.ROOT_URL, reverse("podcast-rss", args=(self.slug,)))

    def __str__(self):
        return self.name

    def update_from_feed(self, feed: feedparser.FeedParserDict):
        from podcasts.models import Category
        from users.models import User

        self.name = markdownify(feed.title)

        if "description" in feed:
            self.description = markdownify(feed.description)

        if "image" in feed and "href" in feed.image and feed.image.href:
            logger.info("Importing cover image: %s", feed.image.href)
            response = requests.get(feed.image.href, timeout=10)
            if response.ok:
                suffix = ""
                content_type = response.headers.get("Content-Type", "")
                if content_type:
                    suffix = mimetypes.guess_extension(content_type) or ("." + content_type.split("/")[-1])
                delete_storage_file(self.cover)
                self.cover.save(
                    name=f"cover{suffix}",
                    content=ImageFile(file=BytesIO(response.content)),
                    save=False,
                )
                self.handle_uploaded_cover()

        if "language" in feed:
            self.language = feed.language

        self.save()

        if "tags" in feed:
            tags = [t["term"] for t in feed.tags]
            self.categories.add(*list(Category.objects.filter(Q(cat__in=tags) | Q(sub__in=tags))))
        if "authors" in feed:
            self.owners.add(*list(User.objects.filter(email__in=[a["email"] for a in feed.authors if "email" in a])))

    def handle_uploaded_banner(self, save: bool = False):
        downscale_image(self.banner, max_width=960, max_height=320, save=save)

    def handle_uploaded_cover(self, save: bool = False):
        delete_storage_file(self.cover_thumbnail)
        if self.cover:
            mimetype = generate_thumbnail(self.cover, self.cover_thumbnail, 150, save)
            self.cover_mimetype = mimetype
            self.cover_thumbnail_mimetype = mimetype
        else:
            self.cover_mimetype = None
            self.cover_thumbnail_mimetype = None
        if save:
            self.save()

    def handle_uploaded_favicon(self, save: bool = False):
        downscale_image(self.favicon, max_width=100, max_height=100, save=save)
