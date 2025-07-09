from typing import TYPE_CHECKING

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from markdown import markdown

from spodcat.markdown import MarkdownExtension
from spodcat.model_mixin import ModelMixin


if TYPE_CHECKING:
    from .podcast_content import PodcastContent


class Comment(ModelMixin, models.Model):
    created = models.DateTimeField(auto_now_add=True, verbose_name=_("created"))
    is_approved = models.BooleanField(default=False, verbose_name=_("is approved"))
    name = models.CharField(max_length=50, verbose_name=_("name"))
    podcast_content = models.ForeignKey["PodcastContent"](
        "spodcat.PodcastContent",
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("podcast content"),
    )
    text = models.TextField(verbose_name=_("text"))

    class Meta:
        ordering = ["created"]
        verbose_name = _("comment")
        verbose_name_plural = _("comments")

    @property
    def text_html(self) -> str:
        return markdown(self.text, extensions=["nl2br", "smarty", MarkdownExtension()])

    # pylint: disable=no-member
    def has_change_permission(self, request):
        return isinstance(request.user, AbstractUser) and (
            request.user.is_superuser or
            request.user == self.podcast_content.podcast.owner or
            request.user in self.podcast_content.podcast.authors.all()
        )
