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
    FONT_FAMILIES = [
        "Anton",
        "Deutsche Uncialis",
        "Fascinate Inline",
        "Futura Display BQ",
        "Limelight",
        "Lobster",
        "Roboto Black",
        "Roboto Serif Bold",
        "Unifraktur Cook",
    ]
    FONT_SIZES = ["small", "normal", "large"]

    slug = models.SlugField(primary_key=True, validators=[podcast_slug_validator], help_text="Will be used in URLs.")
    name = models.CharField(max_length=100)
    tagline = models.CharField(max_length=500, null=True, blank=True, default=None)
    description = MartorField(null=True, default=None, blank=True)
    cover = models.ImageField(
        null=True,
        default=None,
        blank=True,
        validators=[podcast_cover_validator],
        upload_to=podcast_image_path,
        help_text="This is the round 'avatar' image.",
    )
    cover_height = models.PositiveIntegerField(null=True, default=None)
    cover_width = models.PositiveIntegerField(null=True, default=None)
    cover_mimetype = models.CharField(max_length=50, null=True, default=None)
    cover_thumbnail = models.ImageField(
        null=True,
        default=None,
        blank=True,
        upload_to=podcast_image_path,
    )
    cover_thumbnail_height = models.PositiveIntegerField(null=True, default=None)
    cover_thumbnail_width = models.PositiveIntegerField(null=True, default=None)
    cover_thumbnail_mimetype = models.CharField(max_length=50, null=True, default=None)
    banner = models.ImageField(
        null=True,
        default=None,
        blank=True,
        upload_to=podcast_image_path,
        verbose_name="Banner image",
        help_text="Should be >= 960px wide and have aspect ratio 3:1.",
    )
    banner_height = models.PositiveIntegerField(null=True, default=None)
    banner_width = models.PositiveIntegerField(null=True, default=None)
    favicon = models.ImageField(null=True, default=None, blank=True, upload_to=podcast_image_path)
    favicon_content_type = models.CharField(null=True, default=None, blank=True, max_length=50)
    authors: "RelatedManager[User]" = models.ManyToManyField("users.User", related_name="podcasts", blank=True)
    owner: "User | None" = models.ForeignKey(
        "users.User",
        related_name="owned_podcasts",
        blank=True,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
    )
    language = models.CharField(max_length=5, choices=get_language_choices, null=True, blank=True, default=None)
    categories: "RelatedManager[Category]" = models.ManyToManyField("podcasts.Category", blank=True)
    name_font_family = models.CharField(
        max_length=50,
        choices=[(c, c) for c in FONT_FAMILIES],
        default="Unifraktur Cook",
    )
    name_font_size = models.CharField(
        max_length=10,
        choices=[(c, c) for c in FONT_SIZES],
        default="normal",
    )
    enable_comments = models.BooleanField(default=False)
    require_comment_approval = models.BooleanField(default=True)

    contents: "PolymorphicManager"
    links: "RelatedManager[PodcastLink]"

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["name"])]

    @property
    def description_html(self) -> str:
        if self.description:
            return markdown(self.description, extensions=["nl2br", "smarty", MarkdownExtension()])
        return ""

    @property
    def frontend_url(self) -> str:
        return urljoin(settings.FRONTEND_ROOT_URL, self.slug)

    @property
    def rss_url(self) -> str:
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
                # pylint: disable=no-member
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
            self.authors.add(*list(User.objects.filter(email__in=[a["email"] for a in feed.authors if "email" in a])))

    # pylint: disable=no-member
    def handle_uploaded_banner(self, save: bool = False):
        downscale_image(self.banner, max_width=960, max_height=320, save=save)
        if self.banner:
            self.banner_height = self.banner.height
            self.banner_width = self.banner.width
        else:
            self.banner_height = None
            self.banner_width = None
        if save:
            self.save()

    # pylint: disable=no-member
    def handle_uploaded_cover(self, save: bool = False):
        delete_storage_file(self.cover_thumbnail)
        if self.cover:
            mimetype = generate_thumbnail(self.cover, self.cover_thumbnail, 150, save)
            self.cover_mimetype = mimetype
            self.cover_thumbnail_mimetype = mimetype
            self.cover_height = self.cover.height
            self.cover_width = self.cover.width
            self.cover_thumbnail_height = self.cover_thumbnail.height
            self.cover_thumbnail_width = self.cover_thumbnail.width
        else:
            self.cover_mimetype = None
            self.cover_thumbnail_mimetype = None
            self.cover_height = None
            self.cover_width = None
            self.cover_thumbnail_height = None
            self.cover_thumbnail_width = None
        if save:
            self.save()

    def handle_uploaded_favicon(self, save: bool = False):
        downscale_image(self.favicon, max_width=100, max_height=100, save=save)
