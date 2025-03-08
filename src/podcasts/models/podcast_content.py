from typing import TYPE_CHECKING

from django.contrib import admin
from django.db import models
from django.utils import timezone
from markdown import markdown
from martor.models import MartorField
from polymorphic.models import PolymorphicModel
from slugify import slugify

from podcasts.markdown import MarkdownExtension


if TYPE_CHECKING:
    from podcasts.models import Podcast


class PodcastContent(PolymorphicModel):
    slug = models.SlugField(primary_key=True, max_length=100)
    name = models.CharField(max_length=100)
    description = MartorField(null=True, default=None, blank=True)
    podcast: "Podcast" = models.ForeignKey("podcasts.Podcast", on_delete=models.PROTECT, related_name="contents")
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

    def __str__(self):
        return self.name

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
