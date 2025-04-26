import itertools
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Iterable, TypedDict

from django.db.models import (
    DurationField,
    F,
    FloatField,
    Q,
    QuerySet,
    Sum,
    Value as V,
)
from django.db.models.functions import Cast, Coalesce, Concat, Round
from django.utils.timezone import get_current_timezone


if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser, AnonymousUser

    from logs.models import PodcastEpisodeAudioRequestLog

    class ChartQuerySetValues(TypedDict):
        name: str
        slug: str
        date: date
        y: int


class ChartData:
    class DataSet(TypedDict):
        class DataPoint(TypedDict):
            x: int
            y: int

        label: str
        data: list[DataPoint]

    datasets: list[DataSet]
    start_date: date
    end_date: date
    _epoch: datetime

    def __init__(self, data: Iterable["ChartQuerySetValues"], start_date: date, end_date: date):
        self.datasets = []
        self.start_date = start_date
        self.end_date = end_date
        self._epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)

        for key, values in itertools.groupby(data, key=lambda v: tuple([v["slug"], v["name"]])):
            self.datasets.append({
                "label": key[1],
                "data": [{"x": self._date_to_ms(v["date"]), "y": v["y"]} for v in values],
            })

    def _date_to_ms(self, d: date):
        dt = datetime(d.year, d.month, d.day, tzinfo=get_current_timezone())
        return int((dt - self._epoch).total_seconds() * 1000)

    def fill_empty_points(self):
        days = (self.end_date - self.start_date).days + 1
        dates = [self._date_to_ms(self.start_date + timedelta(days=d)) for d in range(days)]

        for dataset in self.datasets:
            new_data: list[ChartData.DataSet.DataPoint] = []
            datadict = {d["x"]: d["y"] for d in dataset["data"]}
            for d in dates:
                new_data.append({"x": d, "y": datadict.get(d, 0)})
            dataset["data"] = new_data


class PodcastEpisodeAudioRequestLogQuerySet(QuerySet["PodcastEpisodeAudioRequestLog"]):
    def filter_by_user(self, user: "AbstractUser | AnonymousUser"):
        if user.is_superuser:
            return self
        if not user.is_staff:
            return self.none()
        return self.filter(Q(episode__podcast__owner=user) | Q(episode__podcast__authors=user))

    def get_episode_chart_data(self, start_date: date, end_date: date):
        qs = (
            self.order_by()
            .values(name=F("episode__name"), slug=F("episode__slug"), date=F("created__date"))
            .with_play_time_alias()
            .annotate(y=Sum(F("play_time")))
            .exclude(y=0.0)
            .values("name", "slug", "date", "y")
            .order_by("slug", "date")
        )
        return ChartData(qs, start_date, end_date)

    def get_podcast_chart_data(self, start_date: date, end_date: date):
        qs = (
            self.order_by()
            .values(name=F("episode__podcast__name"), slug=F("episode__podcast__slug"), date=F("created__date"))
            .with_play_time_alias()
            .annotate(y=Sum(F("play_time")))
            .values("name", "slug", "date", "y")
            .order_by("slug", "date")
        )
        return ChartData(qs, start_date, end_date)

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
        return (
            self
            .filter(**filters)
            .order_by()
            .values(*filters.keys())
            .with_play_time_alias()
            .annotate(play_time=Cast(Concat(Sum(F("play_time")), V(" seconds")), DurationField()))
            .values("play_time")
        )

    def with_play_time_alias(self):
        return self.alias(
            play_time=Round(
                Cast(F("response_body_size"), FloatField()) /
                F("episode__audio_file_length") *
                F("episode__duration_seconds")
            ),
        )

    def with_percent_fetched(self):
        return self.with_quota_fetched_alias().annotate(
            percent_fetched=Cast(F("quota_fetched") * V(100), FloatField()),
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
    ):
        ...
