from typing import TYPE_CHECKING, Any, TypeVar, cast

from django.contrib.auth.models import AbstractUser
from django.db.models import Exists, Max, OuterRef, Q, QuerySet
from polymorphic.query import PolymorphicQuerySet

from spodcat.utils import round_to_whole_hour


if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

    from spodcat.models import Podcast, PodcastContent

    _PCT = TypeVar("_PCT", bound=PodcastContent)


class PodcastQuerySet(QuerySet["Podcast"]):
    @classmethod
    def as_manager(cls) -> "PodcastManager":
        return cast("PodcastManager", super().as_manager())

    def filter_by_user(self, user: "AnonymousUser | AbstractBaseUser"):
        if isinstance(user, AbstractUser) and user.is_superuser:
            return self
        if user.is_authenticated:
            return self.filter(Q(owner=user) | Q(authors=user))
        return self.none()

    def order_by_last_content(self, reverse: bool = False):
        field_name = "last_content" if not reverse else "-last_content"

        return self.alias(
            last_content=Max(
                "contents__published",
                filter=Q(contents__is_draft=False, contents__published__lte=round_to_whole_hour()),
            ),
        ).order_by(field_name, "name")


class PodcastContentQuerySet(PolymorphicQuerySet["_PCT"]):
    @classmethod
    def as_manager(cls) -> "PodcastContentManager":
        return cast("PodcastContentManager", super().as_manager())

    def partial(self):
        return self.only(
            "Episode___audio_file",
            "Episode___duration_seconds",
            "Episode___image_thumbnail",
            "Episode___number",
            "Episode___podcastcontent_ptr_id",
            "Episode___season2",
            "id",
            "name",
            "podcast",
            "polymorphic_ctype_id",
            "published",
            "slug",
        )

    def published(self):
        return self.filter(published__lte=round_to_whole_hour())

    def listed(self):
        return self.published().filter(is_draft=False)

    def with_has_chapters(self):
        from spodcat.models import EpisodeChapter, EpisodeSong

        return self.alias(
            _has_songs=Exists(EpisodeSong.objects.filter(episode=OuterRef("pk"))),
            _has_chapters=Exists(EpisodeChapter.objects.filter(episode=OuterRef("pk"))),
        ).annotate(has_chapters=Q(_has_songs=True) | Q(_has_chapters=True))

    def with_has_songs(self):
        from spodcat.models import EpisodeSong

        return self.annotate(has_songs=Exists(EpisodeSong.objects.filter(episode=OuterRef("pk"))))


if TYPE_CHECKING:
    from django.db.models.manager import Manager
    from polymorphic.managers import PolymorphicManager

    class PodcastContentManager(PolymorphicManager[_PCT], PodcastContentQuerySet[_PCT]):
        def filter(self, *args: Any, **kwargs: Any) -> PodcastContentQuerySet[_PCT]: ...
        def select_related(self, *fields: Any) -> PodcastContentQuerySet[_PCT]: ...

    class PodcastManager(Manager[Podcast], PodcastQuerySet):
        ...
