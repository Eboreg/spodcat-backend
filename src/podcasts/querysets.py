from typing import TYPE_CHECKING, TypeVar

from django.db.models import Exists, OuterRef, Q, QuerySet
from django.utils import timezone
from polymorphic.query import PolymorphicQuerySet


if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser, AnonymousUser

    from podcasts.models import Podcast, PodcastContent

    _T = TypeVar("_T", bound=PodcastContent)


class PodcastQuerySet(QuerySet["Podcast"]):
    def filter_by_user(self, user: "AnonymousUser | AbstractUser"):
        if user.is_superuser:
            return self
        return self.filter(Q(owner=user) | Q(authors=user))


class PodcastContentQuerySet(PolymorphicQuerySet["_T"]):
    def partial(self):
        return self.only(
            "Episode___audio_file",
            "Episode___duration_seconds",
            "Episode___number",
            "Episode___podcastcontent_ptr_id",
            "name",
            "podcast",
            "polymorphic_ctype_id",
            "published",
            "slug",
        )

    def visible(self):
        return self.filter(published__lte=timezone.now().date(), is_draft=False)

    def with_has_chapters(self):
        from podcasts.models import EpisodeChapter, EpisodeSong

        return self.alias(
            _has_songs=Exists(EpisodeSong.objects.filter(episode=OuterRef("pk"))),
            _has_chapters=Exists(EpisodeChapter.objects.filter(episode=OuterRef("pk"))),
        ).annotate(has_chapters=Q(_has_songs=True) | Q(_has_chapters=True))

    def with_has_songs(self):
        from podcasts.models import EpisodeSong

        return self.annotate(has_songs=Exists(EpisodeSong.objects.filter(episode=OuterRef("pk"))))


if TYPE_CHECKING:
    from django.db.models.manager import Manager
    from polymorphic.managers import PolymorphicManager

    class PodcastContentManager(PolymorphicManager[_T], PodcastContentQuerySet[_T]):
        ...

    class PodcastManager(Manager[Podcast], PodcastQuerySet):
        ...
