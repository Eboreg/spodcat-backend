from typing import TYPE_CHECKING

from django.db.models import (
    DurationField,
    F,
    FloatField,
    IntegerField,
    QuerySet,
    Sum,
    Value as V,
)
from django.db.models.functions import Cast, Coalesce, Round, Concat


if TYPE_CHECKING:
    from logs.models import PodcastEpisodeAudioRequestLog


class PodcastEpisodeAudioRequestLogQuerySet(QuerySet["PodcastEpisodeAudioRequestLog"]):
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
            percent_fetched=Cast(F("quota_fetched") * V(100), IntegerField()),
        )

    def with_quota_fetched_alias(self):
        return self.alias(
            quota_fetched=Cast(F("response_body_size"), FloatField()) / F("episode__audio_file_length"),
        )
