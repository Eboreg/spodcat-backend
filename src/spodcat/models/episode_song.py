from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import gettext_lazy as _

from .episode_chapter import AbstractEpisodeChapter


if TYPE_CHECKING:
    from .artist import Artist
    from .episode import Episode


class EpisodeSong(AbstractEpisodeChapter):
    artists: "models.ManyToManyField[Artist]" = models.ManyToManyField(
        "spodcat.Artist",
        related_name="songs",
        blank=True,
        verbose_name=_("artists"),
    )
    comment = models.CharField(max_length=100, null=True, default=None, blank=True, verbose_name=_("comment"))
    episode: "Episode" = models.ForeignKey(
        "spodcat.Episode",
        on_delete=models.CASCADE,
        related_name="songs",
        verbose_name=_("episode"),
    )
    title = models.CharField(max_length=100, verbose_name=_("title"))

    class Meta:
        ordering = ["start_time"]
        indexes = [models.Index(fields=["start_time"])]
        verbose_name = _("episode song")
        verbose_name_plural = _("episode songs")

    def __str__(self):
        return self.title

    @property
    # pylint: disable=no-member
    def formatted_title(self):
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
