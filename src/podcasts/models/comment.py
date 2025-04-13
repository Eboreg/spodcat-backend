from django.db import models
from markdown import markdown

from podcasts.markdown import MarkdownExtension


class Comment(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    name = models.CharField(max_length=100)
    podcast_content = models.ForeignKey("podcasts.PodcastContent", on_delete=models.CASCADE, related_name="comments")
    text = models.TextField()

    class Meta:
        ordering = ["created"]

    @property
    def text_html(self) -> str:
        return markdown(self.text, extensions=["nl2br", "smarty", MarkdownExtension()])
