from typing import TYPE_CHECKING

from django.db import models

from utils.model_mixin import ModelMixin


if TYPE_CHECKING:
    from podcasts.models import Artist, Episode


class EpisodeSong(ModelMixin, models.Model):
    artists: "models.ManyToManyField[Artist]" = models.ManyToManyField(
        "podcasts.Artist",
        related_name="songs",
        blank=True,
    )
    comment = models.CharField(max_length=100, null=True, default=None, blank=True)
    episode: "Episode" = models.ForeignKey("podcasts.Episode", on_delete=models.CASCADE, related_name="songs")
    name = models.CharField(max_length=100)
    timestamp = models.PositiveIntegerField()

    class Meta:
        ordering = ["timestamp"]
        indexes = [models.Index(fields=["timestamp"])]

    def __str__(self):
        return self.name

    @property
    # pylint: disable=no-member
    def chapter_string(self):
        artists = "/".join(a.name for a in self.artists.all())
        result = f"{artists} - " if artists else ""
        result += self.name
        if self.comment:
            result += f" ({self.comment})"
        return result

    # pylint: disable=no-member
    def has_change_permission(self, request):
        return (
            request.user.is_superuser or
            request.user == self.episode.podcast.owner or
            request.user in self.episode.podcast.authors.all()
        )
