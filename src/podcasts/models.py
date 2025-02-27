from html import escape
from typing import TYPE_CHECKING, BinaryIO

from django.contrib import admin
from django.db import models
from django.utils import timezone
from iso639 import iter_langs
from markdown import markdown
from mdeditor.fields import MDTextField
from slugify import slugify
from polymorphic.models import PolymorphicModel

from podcasts.markdown import MarkdownExtension
from podcasts.utils import get_audio_file_dbfs_array
from podcasts.validators import podcast_cover_validator


if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager
    from polymorphic.managers import PolymorphicManager

    from users.models import User


def get_language_choices():
    return [(l.pt1, l.name) for l in iter_langs() if l.pt1]


class Category(models.Model):
    cat = models.CharField(max_length=50)
    sub = models.CharField(max_length=50, null=True, default=None)

    class Meta:
        ordering = ["cat", "sub"]
        indexes = [models.Index(fields=["cat", "sub"])]

    def __str__(self):
        if self.sub:
            return f"{self.cat} / {self.sub}"
        return self.cat

    def to_dict(self):
        if self.sub:
            return {"cat": escape(self.cat), "sub": escape(self.sub)}
        return {"cat": escape(self.cat)}


def podcast_link_icon_path(instance: "PodcastLink", filename: str):
    return f"{instance.podcast.slug}/images/links/{filename}"


class PodcastLink(models.Model):
    class Icon(models.TextChoices):
        FACEBOOK = "facebook", "Facebook"
        PATREON = "patreon", "Patreon"
        DISCORD = "discord", "Discord"
        APPLE = "apple", "Apple"
        ANDROID = "android", "Android"
        SPOTIFY = "spotify", "Spotify"
        ITUNES = "itunes", "Itunes"

    class Theme(models.TextChoices):
        PRIMARY = "primary", "Primary"
        SECONDARY = "secondary", "Secondary"
        TERTIARY = "tertiary", "Tertiary"

    icon = models.CharField(max_length=10, choices=Icon, null=True, default=None)
    custom_icon = models.ImageField(upload_to=podcast_link_icon_path, null=True, default=None, blank=True)
    url = models.URLField()
    label = models.CharField(max_length=100)
    podcast = models.ForeignKey("podcasts.Podcast", on_delete=models.CASCADE, related_name="links")
    order = models.PositiveSmallIntegerField(default=0)
    theme = models.CharField(max_length=10, choices=Theme, default=Theme.PRIMARY)

    class Meta:
        ordering = ["order"]
        indexes = [models.Index(fields=["order"])]


def podcast_image_path(instance: "Podcast", filename: str):
    return f"{instance.slug}/images/{filename}"


class Podcast(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=100)
    tagline = models.CharField(max_length=500, null=True, blank=True, default=None)
    description = MDTextField(null=True, default=None, blank=True)
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
    cover_thumbnail = models.ImageField(null=True, default=None, blank=True, upload_to=podcast_image_path)
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
        return self.contents.instance_of(Episode)

    def __str__(self):
        return self.name


def episode_audio_file_path(instance: "Episode", filename: str):
    return f"{instance.podcast.slug}/episodes/{filename}"


class PodcastContent(PolymorphicModel):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=100)
    description = MDTextField(null=True, default=None, blank=True)
    podcast: "Podcast" = models.ForeignKey("Podcast", on_delete=models.PROTECT, related_name="contents")
    published = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True)
    is_draft = models.BooleanField(verbose_name="Draft", default=False)

    class Meta:
        ordering = ["-published"]
        indexes = [models.Index(fields=["-published"])]

    @property
    def description_html(self):
        if self.description:
            return markdown(self.description, extensions=["nl2br", "smarty", MarkdownExtension()])
        return None

    def _get_base_slug(self):
        return slugify(self.name)

    @admin.display(boolean=True)
    def is_published(self):
        return self.published <= timezone.now() and not self.is_draft

    def generate_slug(self):
        slugs = [e.slug for e in self._meta.model.objects.filter(podcast=self.podcast)]
        base_slug = self._get_base_slug()
        slug = base_slug
        i = 1

        while slug in slugs:
            slug = f"{base_slug}-{i}"
            i += 1

        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_slug()

        super().save(*args, **kwargs)


class Episode(PodcastContent):
    number = models.PositiveSmallIntegerField(null=True, default=None, blank=True)
    audio_file = models.FileField(upload_to=episode_audio_file_path)
    duration_seconds = models.FloatField(blank=True, verbose_name="duration")
    dbfs_array = models.JSONField(blank=True, default=list)
    audio_content_type = models.CharField(max_length=100, blank=True)
    audio_file_length = models.PositiveIntegerField(blank=True)

    def __str__(self):
        if self.number is not None:
            return f"[{self.number}] {self.name}"
        return self.name

    def _get_base_slug(self):
        base_slug = slugify(self.name)
        if self.number is not None:
            base_slug = f"{self.number}-" + base_slug
        return base_slug

    def update_audio_file_dbfs_array(self, file: BinaryIO, format_name: str, save: bool = True):
        self.dbfs_array = get_audio_file_dbfs_array(file, format_name)

        if save:
            self.save()
