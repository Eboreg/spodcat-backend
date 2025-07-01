import re
import uuid
from typing import TYPE_CHECKING, Self
from urllib.parse import urljoin

from django.contrib import admin
from django.db import models
from django.db.models import Case, Q, Value as V, When
from django.db.models.functions import Now
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from markdown import markdown
from martor.models import MartorField
from polymorphic.models import PolymorphicModel
from slugify import slugify

from spodcat.markdown import MarkdownExtension
from spodcat.models.querysets import PodcastContentQuerySet
from spodcat.settings import spodcat_settings
from spodcat.utils.model_mixin import ModelMixin


if TYPE_CHECKING:
    from spodcat.models import Podcast
    from spodcat.models.querysets import PodcastContentManager


def today():
    return timezone.now().date()


class PodcastContent(ModelMixin, PolymorphicModel):
    created = models.DateTimeField(auto_now_add=True, verbose_name=_("created"))
    description = MartorField(null=True, default=None, blank=True, verbose_name=_("description"))
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    is_draft = models.BooleanField(verbose_name=_("draft"), default=False)
    name = models.CharField(max_length=100, verbose_name=_("name"))
    podcast: "Podcast" = models.ForeignKey("spodcat.Podcast", on_delete=models.PROTECT, related_name="contents")
    published = models.DateField(default=today, verbose_name=_("published"))
    slug = models.SlugField(max_length=100, verbose_name=_("slug"))

    objects: "PodcastContentManager[Self]" = PodcastContentQuerySet.as_manager()

    class Meta:
        ordering = ["-published"]
        indexes = [models.Index(fields=["-published"])]
        constraints = [
            models.UniqueConstraint(fields=["slug", "podcast"], name="podcasts__podcastcontent__slug_podcast__uq"),
        ]
        get_latest_by = "published"
        verbose_name = _("podcast content")
        verbose_name_plural = _("podcast contents")

    @property
    def description_html(self) -> str:
        if self.description:
            return markdown(self.description, extensions=["nl2br", "smarty", MarkdownExtension()])
        return ""

    @property
    def description_text(self) -> str:
        if self.description:
            # Basic stripping of Markdown image tags:
            return re.sub(r"[\r\n]*!\[.*?\]\(.*?\)", "", self.description).strip()
        return ""

    @property
    # pylint: disable=no-member
    def frontend_url(self) -> str:
        instance_class = self.get_real_instance_class()

        if self.is_draft:
            return urljoin(
                spodcat_settings.FRONTEND_ROOT_URL,
                f"{self.podcast.slug}/{instance_class._meta.model_name}/draft/{self.id}",
            )

        return urljoin(
            spodcat_settings.FRONTEND_ROOT_URL,
            f"{self.podcast.slug}/{instance_class._meta.model_name}/{self.slug}",
        )

    def __str__(self):
        return self.name

    def _get_base_slug(self) -> str:
        return slugify(self.name)

    def generate_slug(self) -> str:
        existing = [e.slug for e in self._meta.model.objects.filter(podcast=self.podcast)]
        existing += ["draft"]
        base_slug = self._get_base_slug()
        slug = base_slug
        i = 1

        while slug in existing:
            slug = f"{base_slug}-{i}"
            i += 1

        return slug

    # pylint: disable=no-member
    def has_change_permission(self, request):
        return (
            request.user.is_superuser or
            request.user == self.podcast.owner or
            request.user in self.podcast.authors.all()
        )

    @admin.display(
        boolean=True,
        description=_("visible"),
        ordering=Case(When(Q(is_draft=False, published__lte=Now()), then=V(1)), default=V(0)),
    )
    def is_visible(self) -> bool:
        return self.published <= timezone.now().date() and not self.is_draft

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_slug()

        super().save(*args, **kwargs)
