from collections.abc import Iterable

from django.contrib import admin
from django.db import models
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from spodcat.contrib.admin.filters import ArtistSongCountFilter
from spodcat.contrib.admin.mixin import AdminMixin, StaticRSSMixin
from spodcat.models import Artist, EpisodeSong


class ArtistSongInline(AdminMixin, admin.TabularInline):
    extra = 0
    fields = ["song", "episode"]
    model = EpisodeSong.artists.through
    readonly_fields = ["song", "episode"]
    verbose_name = _("song")
    verbose_name_plural = _("songs")

    def episode(self, obj):
        return obj.episodesong.episode

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("episodesong__episode")

    def has_add_permission(self, request, obj):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def song(self, obj):
        return obj.episodesong.title


class ArtistAdmin(AdminMixin, StaticRSSMixin[Artist], admin.ModelAdmin):
    inlines = [ArtistSongInline]
    list_display = ["name", "song_count"]
    list_filter = [ArtistSongCountFilter]
    save_on_top = True
    search_fields = ["name"]

    def get_podcast_slugs_from_instance(self, obj: Artist) -> Iterable[str]:
        return set(obj.songs.values_list("episode__podcast__slug", flat=True))

    def get_podcast_slugs_from_queryset(self, queryset: models.QuerySet[Artist, Artist]) -> Iterable[str]:
        return set(queryset.values_list("songs__episode__podcast__slug", flat=True))

    def get_queryset(self, request: HttpRequest):
        return super().get_queryset(request).annotate(song_count=models.Count("songs"))

    @admin.display(description=_("songs"), ordering="song_count")
    def song_count(self, obj):
        return obj.song_count
