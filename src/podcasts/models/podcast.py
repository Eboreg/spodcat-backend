import logging
import mimetypes
import re
import uuid
from base64 import b64encode
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

from podcasts.querysets import PodcastQuerySet
from podcasts.validators import podcast_cover_validator, podcast_slug_validator
from utils import delete_storage_file, downscale_image, generate_thumbnail
from utils.markdown import MarkdownExtension
from utils.model_mixin import ModelMixin


if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager

    from podcasts.models import Category, PodcastLink
    from podcasts.querysets import PodcastContentManager, PodcastManager
    from users.models import User


logger = logging.getLogger(__name__)


def get_language_choices():
    return [(l.pt1, l.name) for l in iter_langs() if l.pt1]


def podcast_image_path(instance: "Podcast", filename: str):
    return f"{instance.slug}/images/{filename}"


class Podcast(ModelMixin, models.Model):
    FONT_FAMILIES = [
        "Anton",
        "Bauhaus 93",
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

    authors: "RelatedManager[User]" = models.ManyToManyField("users.User", related_name="podcasts", blank=True)
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
    categories: "RelatedManager[Category]" = models.ManyToManyField("podcasts.Category", blank=True)
    cover = models.ImageField(
        null=True,
        default=None,
        blank=True,
        validators=[podcast_cover_validator],
        upload_to=podcast_image_path,
        help_text="This is the round 'avatar' image.",
    )
    cover_height = models.PositiveIntegerField(null=True, default=None)
    cover_mimetype = models.CharField(max_length=50, null=True, default=None)
    cover_thumbnail = models.ImageField(
        null=True,
        default=None,
        blank=True,
        upload_to=podcast_image_path,
    )
    cover_thumbnail_height = models.PositiveIntegerField(null=True, default=None)
    cover_thumbnail_mimetype = models.CharField(max_length=50, null=True, default=None)
    cover_thumbnail_width = models.PositiveIntegerField(null=True, default=None)
    cover_width = models.PositiveIntegerField(null=True, default=None)
    description = MartorField(null=True, default=None, blank=True)
    enable_comments = models.BooleanField(default=False)
    favicon = models.ImageField(null=True, default=None, blank=True, upload_to=podcast_image_path)
    favicon_content_type = models.CharField(null=True, default=None, blank=True, max_length=50)
    language = models.CharField(max_length=5, choices=get_language_choices, null=True, blank=True, default=None)
    name = models.CharField(max_length=100)
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
    owner: "User" = models.ForeignKey("users.User", related_name="owned_podcasts", on_delete=models.PROTECT)
    require_comment_approval = models.BooleanField(default=True)
    slug = models.SlugField(primary_key=True, validators=[podcast_slug_validator], help_text="Will be used in URLs.")
    tagline = models.CharField(max_length=500, null=True, blank=True, default=None)
    custom_guid = models.UUIDField(
        null=True,
        default=None,
        blank=True,
        verbose_name="Custom GUID",
        help_text="Don't set if you don't know what you're doing. " + \
            "Ref: https://podcasting2.org/podcast-namespace/tags/guid",
    )

    contents: "PodcastContentManager"
    links: "RelatedManager[PodcastLink]"

    objects: "PodcastManager" = PodcastQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["name"])]

    @property
    def description_html(self) -> str:
        if self.description:
            return markdown(self.description, extensions=["nl2br", "smarty", MarkdownExtension()])
        return ""

    @property
    def episodes_fm_url(self) -> str:
        return "https://episodes.fm/" + b64encode(self.rss_url.encode()).decode().strip("=")

    @property
    def frontend_url(self) -> str:
        return urljoin(settings.FRONTEND_ROOT_URL, self.slug)

    @property
    def guid(self):
        if self.custom_guid:
            return self.custom_guid
        url = re.sub(r"^\w+://", "", self.rss_url).strip("/")
        return uuid.uuid5(uuid.UUID("ead4c236-bf58-58c6-a2c6-a6b28d128cb6"), url)

    @property
    def rss_url(self) -> str:
        return urljoin(settings.ROOT_URL, reverse("podcast-rss", args=(self.slug,)))

    def __str__(self):
        return self.name

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

    def has_change_permission(self, request):
        return request.user.is_superuser or request.user == self.owner or request.user in self.authors.all()

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
