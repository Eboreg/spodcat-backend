from django.db import models
from markdown import markdown

from podcasts.markdown import MarkdownExtension


class Comment(models.Model):
    podcast_content = models.ForeignKey("podcasts.PodcastContent", on_delete=models.CASCADE, related_name="comments")
    name = models.CharField(max_length=100)
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        ordering = ["created"]

    @property
    def text_html(self) -> str:
        return markdown(self.text, extensions=["nl2br", "smarty", MarkdownExtension()])
