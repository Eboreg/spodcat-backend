from typing import TYPE_CHECKING

from django.db import models

from podcasts.models.episode_chapter import AbstractEpisodeChapter
from podcasts.types import ChapterDict


if TYPE_CHECKING:
    from podcasts.models import Artist, Episode


class EpisodeSong(AbstractEpisodeChapter):
    artists: "models.ManyToManyField[Artist]" = models.ManyToManyField(
        "podcasts.Artist",
        related_name="songs",
        blank=True,
    )
    comment = models.CharField(max_length=100, null=True, default=None, blank=True)
    episode: "Episode" = models.ForeignKey("podcasts.Episode", on_delete=models.CASCADE, related_name="songs")
    title = models.CharField(max_length=100)

    class Meta:
        ordering = ["start_time"]
        indexes = [models.Index(fields=["start_time"])]

    def __str__(self):
        return self.title

    @property
    # pylint: disable=no-member
    def chapter_string(self):
        artists = "/".join(a.name for a in self.artists.all())
        result = f"{artists} - " if artists else ""
        result += self.title
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

    def to_dict(self) -> ChapterDict:
        return {"title": self.chapter_string, "startTime": self.start_time}
