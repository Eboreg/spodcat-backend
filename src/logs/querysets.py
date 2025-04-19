from typing import TYPE_CHECKING

from django.db.models import (
    F,
    FloatField,
    IntegerField,
    QuerySet,
    Sum,
    Value as V,
)
from django.db.models.functions import Cast, Coalesce


if TYPE_CHECKING:
    from logs.models import PodcastContentAudioRequestLog


class PodcastContentAudioRequestLogQuerySet(QuerySet["PodcastContentAudioRequestLog"]):
    def get_play_count_query(self, **filters):
        return (
            self
            .filter(**filters)
            .order_by()
            .values(*filters.keys())
            .annotate(
                play_count=Coalesce(
                    Sum(Cast(F("response_body_size"), FloatField()) / F("episode__audio_file_length")),
                    V(0.0),
                    output_field=FloatField(),
                ),
            )
            .values("play_count")
        )

    def with_percent_fetched(self):
        return self.with_quota_fetched_alias().annotate(
            percent_fetched=Cast(F("quota_fetched") * V(100), IntegerField()),
        )

    def with_quota_fetched_alias(self):
        return self.alias(
            quota_fetched=Cast(F("response_body_size"), FloatField()) / F("episode__audio_file_length"),
        )

    def with_seconds_fetched(self):
        return self.with_quota_fetched_alias().annotate(
            seconds_fetched=Cast(F("quota_fetched") * F("episode__duration_seconds"), IntegerField()),
        )
