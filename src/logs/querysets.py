from typing import TYPE_CHECKING

from django.db.models import F, FloatField, IntegerField, QuerySet, Value as V
from django.db.models.functions import Cast


if TYPE_CHECKING:
    from logs.models import PodcastContentAudioRequestLog


class PodcastContentAudioRequestLogQuerySet(QuerySet["PodcastContentAudioRequestLog"]):
    def with_percent_fetched(self):
        return self.with_quota_fetched().annotate(percent_fetched=Cast(F("quota_fetched") * V(100), IntegerField()))

    def with_quota_fetched(self):
        return self.annotate(
            quota_fetched=Cast(F("response_body_size"), FloatField()) / F("episode__audio_file_length"),
        )

    def with_seconds_fetched(self):
        return self.with_quota_fetched().annotate(
            seconds_fetched=Cast(F("quota_fetched") * F("episode__duration_seconds"), IntegerField()),
        )
