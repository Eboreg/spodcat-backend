from collections.abc import Iterable

from django.contrib import admin
from django.db import models
from django.db.models import Q
from django.forms import ModelChoiceField
from django.http import HttpRequest
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from spodcat.contrib.admin.mixin import AdminMixin, StaticRSSMixin
from spodcat.models import EpisodeSong
from spodcat.utils import seconds_to_timestamp


class EpisodeSongAdmin(AdminMixin, StaticRSSMixin[EpisodeSong], admin.ModelAdmin):
    filter_horizontal = ["artists"]
    list_display = ["title", "artists_str", "episode_str", "start_time_str"]
    ordering = ["-episode__number", "start_time"]
    save_on_top = True
    search_fields = ["title", "artists__name", "comment"]

    @admin.display(description=_("artists"))
    def artists_str(self, obj: EpisodeSong):
        return mark_safe("<br>".join(self.get_change_link(a, text=a.name) for a in obj.artists.all()))

    @admin.display(description=_("episode"), ordering="episode__number")
    def episode_str(self, obj: EpisodeSong):
        return self.get_change_link(obj.episode)

    def get_form(self, request: HttpRequest, obj: EpisodeSong | None = None, change: bool = False, **kwargs):
        Form = super().get_form(request, obj, change, **kwargs)
        field = Form.base_fields.get("episode")
        if isinstance(field, ModelChoiceField) and field.queryset is not None:
            field.queryset = field.queryset.filter(
                Q(podcast__authors=request.user) | Q(podcast__owner=request.user)
            ).distinct()
        return Form

    def get_podcast_slugs_from_instance(self, obj: EpisodeSong) -> Iterable[str]:
        return [obj.episode.podcast.slug]

    def get_podcast_slugs_from_queryset(self, queryset: models.QuerySet[EpisodeSong, EpisodeSong]) -> Iterable[str]:
        return set(queryset.values_list("episode__podcast__slug", flat=True))

    def get_queryset(self, request: HttpRequest):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("artists", "episode__podcast__authors")
            .select_related("episode__podcast__owner")
        )

    @admin.display(description=_("start time"), ordering="start_time")
    def start_time_str(self, obj: EpisodeSong):
        return seconds_to_timestamp(obj.start_time)
