from datetime import date
from typing import TYPE_CHECKING

from django.db.models import (
    Count,
    DurationField,
    F,
    FloatField,
    Q,
    QuerySet,
    Sum,
    Value as V,
)
from django.db.models.functions import Cast, Coalesce, Concat, Round

from spodcat.logs.chart_data import DailyChartData, MonthChartData


if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser, AnonymousUser

    from spodcat.logs.models import (
        PodcastEpisodeAudioRequestLog,
        PodcastRssRequestLog,
    )


class PodcastRssRequestLogQuerySet(QuerySet["PodcastRssRequestLog"]):
    def filter_by_user(self, user: "AbstractUser | AnonymousUser"):
        if user.is_superuser:
            return self
        if not user.is_staff:
            return self.none()
        return self.filter(Q(podcast__owner=user) | Q(podcast__authors=user))

    def get_unique_ips_chart_data(self, start_date: date, end_date: date):
        qs = (
            self.order_by()
            .filter(created__date__gte=start_date, created__date__lte=end_date)
            .values(
                month=F("created__date__month"),
                year=F("created__date__year"),
                name=F("podcast__name"),
                slug=F("podcast__slug"),
            )
            .annotate(y=Count("remote_addr", distinct=True))
            .values("month", "year", "y", "name", "slug")
            .order_by("slug", "year", "month")
        )
        return MonthChartData(qs, start_date, end_date)


class PodcastEpisodeAudioRequestLogQuerySet(QuerySet["PodcastEpisodeAudioRequestLog"]):
    def filter_by_user(self, user: "AbstractUser | AnonymousUser"):
        if user.is_superuser:
            return self
        if not user.is_staff:
            return self.none()
        return self.filter(Q(episode__podcast__owner=user) | Q(episode__podcast__authors=user))

    def get_episode_play_count_chart_data(self, start_date: date, end_date: date):
        qs = (
            self.order_by()
            .filter(created__gte=start_date, created__lte=end_date)
            .values(name=F("episode__name"), slug=F("episode__slug"), date=F("created__date"))
            .alias(plays=Cast(F("response_body_size"), FloatField()) / F("episode__audio_file_length"))
            .annotate(y=Sum(F("plays")))
            .exclude(y=0.0)
            .values("name", "slug", "date", "y")
            .order_by("slug", "date")
        )
        return DailyChartData(qs, start_date, end_date)

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

    def get_play_time_query(self, **filters):
        # Not used, keeping it just in case
        from django.db import connections

        connection = connections[self.db]
        if connection.vendor == "postgresql":
            play_time = Cast(Concat(Sum(F("play_time")), V(" seconds")), DurationField())
        else:
            play_time = Cast(Sum(F("play_time")) * 1_000_000, DurationField())

        return (
            self
            .filter(**filters)
            .order_by()
            .values(*filters.keys())
            .with_play_time_alias()
            .annotate(play_time=play_time)
            .values("play_time")
        )

    def get_podcast_play_count_chart_data(self, start_date: date, end_date: date):
        qs = (
            self.order_by()
            .filter(created__gte=start_date, created__lte=end_date)
            .values(name=F("episode__podcast__name"), slug=F("episode__podcast__slug"), date=F("created__date"))
            .alias(plays=Cast(F("response_body_size"), FloatField()) / F("episode__audio_file_length"))
            .annotate(y=Sum(F("plays")))
            .values("name", "slug", "date", "y")
            .order_by("slug", "date")
        )
        return DailyChartData(qs, start_date, end_date)

    def get_unique_ips_chart_data(self, start_date: date, end_date: date):
        qs = (
            self.order_by()
            .filter(created__date__gte=start_date, created__date__lte=end_date)
            .values(
                month=F("created__date__month"),
                year=F("created__date__year"),
                name=F("episode__podcast__name"),
                slug=F("episode__podcast__slug"),
            )
            .annotate(y=Count("remote_addr", distinct=True))
            .values("month", "year", "y", "name", "slug")
            .order_by("slug", "year", "month")
        )
        return MonthChartData(qs, start_date, end_date)

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

    def with_quota_fetched_alias(self):
        return self.alias(
            quota_fetched=Cast(F("response_body_size"), FloatField()) / F("episode__audio_file_length"),
        )


if TYPE_CHECKING:
    from django.db.models.manager import Manager

    class PodcastEpisodeAudioRequestLogManager(
        Manager[PodcastEpisodeAudioRequestLog],
        PodcastEpisodeAudioRequestLogQuerySet,
    ): ...

    class PodcastRssRequestLogManager(Manager[PodcastRssRequestLog], PodcastRssRequestLogQuerySet): ...
