from typing import TYPE_CHECKING, TypeVar

from django.db.models import Exists, Max, OuterRef, Q, QuerySet
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

    def order_by_last_content(self, reverse: bool = False):
        field_name = "last_content" if not reverse else "-last_content"

        return self.alias(
            last_content=Max(
                "contents__published",
                filter=Q(contents__is_draft=False, contents__published__lte=timezone.localdate()),
            ),
        ).order_by(field_name, "name")


class PodcastContentQuerySet(PolymorphicQuerySet["_T"]):
    def partial(self):
        return self.only(
            "Episode___audio_file",
            "Episode___duration_seconds",
            "Episode___image_thumbnail",
            "Episode___number",
            "Episode___podcastcontent_ptr_id",
            "Episode___season",
            "id",
            "name",
            "podcast",
            "polymorphic_ctype_id",
            "published",
            "slug",
        )

    def published(self):
        return self.filter(published__lte=timezone.now().date())

    def listed(self):
        return self.published().filter(is_draft=False)

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
