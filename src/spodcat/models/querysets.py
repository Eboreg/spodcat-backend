import itertools
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Iterable, TypedDict, TypeVar

from django.db.models import Exists, Max, OuterRef, Q, QuerySet
from django.utils.timezone import get_current_timezone, localdate, now
from polymorphic.query import PolymorphicQuerySet


if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser, AnonymousUser

    from spodcat.models import Podcast, PodcastContent

    _T = TypeVar("_T", bound=PodcastContent)

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
                filter=Q(contents__is_draft=False, contents__published__lte=localdate()),
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
        return self.filter(published__lte=now().date())

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

    class PodcastContentManager(PolymorphicManager[_T], PodcastContentQuerySet[_T]):
        ...

    class PodcastManager(Manager[Podcast], PodcastQuerySet):
        ...
