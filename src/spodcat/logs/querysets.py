import functools
import operator
from datetime import date
from typing import TYPE_CHECKING, Any, TypeVar, cast

from django.contrib.auth.models import AbstractUser
from django.db.models import (
    CharField,
    Count,
    F,
    FloatField,
    Min,
    Q,
    QuerySet,
    Sum,
    Value as V,
)
from django.db.models.functions import Cast, Coalesce, LPad, Round

from spodcat.logs.graph_data import PeriodicalGraphData
from spodcat.time_period import Month, TimePeriod, Week, Year


if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
    from django.db.models import Model

    from spodcat.logs.models import (
        PodcastContentRequestLog,
        PodcastEpisodeAudioRequestLog,
        PodcastRequestLog,
        PodcastRssRequestLog,
    )

    _Row_co = TypeVar("_Row_co", covariant=True)  # ONLY use together with _Model
    _Model_co = TypeVar("_Model_co", bound=Model, covariant=True)


class BaseRequestLogQuerySet(QuerySet["_Model_co", "_Row_co"]):
    _podcast_field_prefix: str

    def get_monthly_views(self):
        return (
            self
            .order_by()
            .values(
                month=LPad(Cast("created__date__month", CharField()), 2, V("0")),
                year=F("created__date__year"),
            )
            .values("month", "year", views=Count("pk", distinct=True), visitors=Count("remote_addr", distinct=True))
            .order_by("-year", "-month")
        )

    def get_unique_ips_graph_data(
        self,
        period: type[TimePeriod],
        grouped: bool,
        average: bool,
        start_date: date,
        end_date: date,
    ):
        values = {"date": F("created__date")}

        if not average:
            if period is Year:
                values = {"year": F("created__date__year")}
            elif period is Week:
                values = {"year": F("created__date__year"), "week": F("created__date__week")}
            elif period is Month:
                values = {"year": F("created__date__year"), "month": F("created__date__month")}

        earliest_date = self.aggregate(earliest=Min("created__date"))["earliest"]
        qs = (
            self.order_by()
            .filter(created__date__gte=start_date, created__date__lte=end_date)
            .values(
                name=F(f"{self._podcast_field_prefix}__name"),
                slug=F(f"{self._podcast_field_prefix}__slug"),
                **values,
            )
            .annotate(y=Count("remote_addr", distinct=True))
            .values("y", "name", "slug", *values.keys())
            .order_by("slug", *values.keys())
        )

        return PeriodicalGraphData(qs, period, earliest_date, average=average, grouped=grouped)


class PodcastRequestLogQuerySet(BaseRequestLogQuerySet["PodcastRequestLog", "_Row_co"]):
    _podcast_field_prefix = "podcast"

    @classmethod
    def as_manager(cls) -> "PodcastRequestLogManager":
        return cast("PodcastRequestLogManager", super().as_manager())


class PodcastContentRequestLogQuerySet(BaseRequestLogQuerySet["PodcastContentRequestLog", "_Row_co"]):
    _podcast_field_prefix = "content__podcast"

    @classmethod
    def as_manager(cls) -> "PodcastContentRequestLogManager":
        return cast("PodcastContentRequestLogManager", super().as_manager())


class PodcastRssRequestLogQuerySet(BaseRequestLogQuerySet["PodcastRssRequestLog", "_Row_co"]):
    _podcast_field_prefix = "podcast"

    @classmethod
    def as_manager(cls) -> "PodcastRssRequestLogManager":
        return cast("PodcastRssRequestLogManager", super().as_manager())

    def filter_by_user(self, user: "AbstractBaseUser | AnonymousUser"):
        if not isinstance(user, AbstractUser) or not user.is_staff:
            return self.none()
        if user.is_superuser:
            return self
        return self.filter(Q(podcast__owner=user) | Q(podcast__authors=user))


class PodcastEpisodeAudioRequestLogQuerySet(BaseRequestLogQuerySet["PodcastEpisodeAudioRequestLog", "_Row_co"]):
    _podcast_field_prefix = "episode__podcast"

    @classmethod
    def as_manager(cls) -> "PodcastEpisodeAudioRequestLogManager":
        return cast("PodcastEpisodeAudioRequestLogManager", super().as_manager())

    def filter_by_user(self, user: "AbstractBaseUser | AnonymousUser"):
        if not isinstance(user, AbstractUser) or not user.is_staff:
            return self.none()
        if user.is_superuser:
            return self
        return self.filter(Q(episode__podcast__owner=user) | Q(episode__podcast__authors=user))

    def get_episode_play_count_graph_data(self, period: type[TimePeriod], start_date: date, end_date: date):
        earliest_date = self.aggregate(earliest=Min("created__date"))["earliest"]
        qs = (
            self.order_by()
            .filter(created__date__gte=start_date, created__date__lte=end_date)
            .values(name=F("episode__name"), slug=F("episode__slug"), date=F("created__date"))
            .with_quota_fetched_alias()
            .annotate(y=Sum(F("quota_fetched")))
            .exclude(y=0.0)
            .values("name", "slug", "date", "y")
            .order_by("slug", "date", "-y")
        )
        return PeriodicalGraphData(qs, period, earliest_date)

    def get_most_played(self):
        return (
            self.order_by()
            .values(name=F("episode__name"), slug=F("episode__slug"), eid=F("episode__id"))
            .with_quota_fetched_alias()
            .annotate(plays=Sum(F("quota_fetched")), players=Count("remote_addr", distinct=True))
            .values("name", "slug", "plays", "players", "eid")
            .order_by("-plays")
        )

    def get_play_count_query(self, **filters):
        return (
            self
            .filter(**filters)
            .order_by()
            .values(*filters.keys())
            .with_quota_fetched_alias()
            .annotate(play_count=Coalesce(Sum(F("quota_fetched")), V(0.0), output_field=FloatField()))
            .values("play_count")
        )

    def get_ip_count_query(self, **values):
        return (
            self
            .values(**values)
            .exclude(functools.reduce(operator.or_, [Q(**{v: None}) for v in values]))
            .values(*values.keys(), ip_count=Count("remote_addr", distinct=True))
            .order_by("-ip_count")
        )

    def get_podcast_play_count_graph_data(
        self,
        period: type[TimePeriod],
        grouped: bool,
        start_date: date,
        end_date: date,
    ):
        values = {"date": "created__date"}
        order_by = ["date"]
        if grouped:
            values.update({"name": "episode__podcast__name", "slug": "episode__podcast__slug"})
            order_by = ["slug", "name", "date"]

        earliest_date = self.aggregate(earliest=Min("created__date"))["earliest"]
        qs = (
            self.order_by()
            .filter(created__date__gte=start_date, created__date__lte=end_date)
            .values(**{k: F(v) for k, v in values.items()})
            .alias(plays=Cast(F("response_body_size"), FloatField()) / F("episode__audio_file_length"))
            .annotate(y=Sum(F("plays")))
            .values("y", *values.keys())
            .order_by(*order_by)
        )

        return PeriodicalGraphData(qs, period, earliest_date, grouped=grouped)

    def with_quota_fetched(self):
        return self.annotate(
            quota_fetched=Cast(F("response_body_size"), FloatField()) / F("episode__audio_file_length"),
        )

    def with_quota_fetched_alias(self):
        return self.alias(
            quota_fetched=Cast(F("response_body_size"), FloatField()) / F("episode__audio_file_length"),
        )

    def with_percent_fetched(self):
        return self.with_quota_fetched_alias().annotate(
            percent_fetched=Cast(F("quota_fetched") * V(100), FloatField()),
        )

    def with_play_time_alias(self):
        # play_time = seconds as integer
        return self.alias(
            play_time=Round(
                Cast(F("response_body_size"), FloatField()) /
                F("episode__audio_file_length") *
                F("episode__duration_seconds")
            ),
        )

    # pylint: disable=useless-parent-delegation
    def values(self, *fields, **expressions) -> "PodcastEpisodeAudioRequestLogQuerySet[dict[str, Any]]":
        return super().values(*fields, **expressions) # type: ignore


if TYPE_CHECKING:
    from django.db.models.manager import Manager

    class PodcastEpisodeAudioRequestLogManager(
        Manager[PodcastEpisodeAudioRequestLog],
        PodcastEpisodeAudioRequestLogQuerySet,
    ):
        def filter(self, *args: Any, **kwargs: Any) -> PodcastEpisodeAudioRequestLogQuerySet: ...

    class PodcastRssRequestLogManager(Manager[PodcastRssRequestLog], PodcastRssRequestLogQuerySet):
        def filter(self, *args: Any, **kwargs: Any) -> PodcastRssRequestLogQuerySet: ...

    class PodcastContentRequestLogManager(Manager[PodcastContentRequestLog], PodcastContentRequestLogQuerySet):
        def filter(self, *args: Any, **kwargs: Any) -> PodcastContentRequestLogQuerySet: ...

    class PodcastRequestLogManager(Manager[PodcastRequestLog], PodcastRequestLogQuerySet):
        def filter(self, *args: Any, **kwargs: Any) -> PodcastRequestLogQuerySet: ...
