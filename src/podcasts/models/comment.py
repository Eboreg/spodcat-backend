from typing import TYPE_CHECKING

from django.db import models
from markdown import markdown

from utils.markdown import MarkdownExtension
from utils.model_mixin import ModelMixin


if TYPE_CHECKING:
    from podcasts.models import PodcastContent


class Comment(ModelMixin, models.Model):
    created = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    name = models.CharField(max_length=50)
    podcast_content: "PodcastContent" = models.ForeignKey(
        "podcasts.PodcastContent",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    text = models.TextField()

    class Meta:
        ordering = ["created"]

    @property
    def text_html(self) -> str:
        return markdown(self.text, extensions=["nl2br", "smarty", MarkdownExtension()])

    # pylint: disable=no-member
    def has_change_permission(self, request):
        return (
            request.user.is_superuser or
            request.user == self.podcast_content.podcast.owner or
            request.user in self.podcast_content.podcast.authors.all()
        )
