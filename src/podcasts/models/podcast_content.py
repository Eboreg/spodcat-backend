import uuid
from typing import TYPE_CHECKING, Self

from django.contrib import admin
from django.db import models
from django.db.models import Case, Q, Value as V, When
from django.db.models.functions import Now
from django.utils import timezone
from markdown import markdown
from martor.models import MartorField
from polymorphic.models import PolymorphicModel
from slugify import slugify

from podcasts.markdown import MarkdownExtension
from podcasts.querysets import PodcastContentQuerySet


if TYPE_CHECKING:
    from podcasts.models import Podcast


class PodcastContent(PolymorphicModel):
    slug = models.SlugField(max_length=100)
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=100)
    description = MartorField(null=True, default=None, blank=True)
    podcast: "Podcast" = models.ForeignKey("podcasts.Podcast", on_delete=models.PROTECT, related_name="contents")
    published = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True)
    is_draft = models.BooleanField(verbose_name="Draft", default=False)

    objects: models.Manager[Self] = PodcastContentQuerySet.as_manager()

    class Meta:
        ordering = ["-published"]
        indexes = [models.Index(fields=["-published"])]
        constraints = [
            models.UniqueConstraint(fields=["slug", "podcast"], name="podcasts__podcastcontent__slug_podcast__uq"),
        ]

    @property
    def description_html(self) -> str:
        if self.description:
            return markdown(self.description, extensions=["nl2br", "smarty", MarkdownExtension()])
        return ""

    def __str__(self):
        return self.name

    def _get_base_slug(self) -> str:
        return slugify(self.name)

    @admin.display(
        boolean=True,
        description="visible",
        ordering=Case(When(Q(is_draft=False, published__lte=Now()), then=V(1)), default=V(0)),
    )
    def is_visible(self) -> bool:
        return self.published <= timezone.now() and not self.is_draft

    def generate_slug(self) -> str:
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
