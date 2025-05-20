from django.contrib import admin

from podcasts.fields import ArtistMultipleChoiceField
from podcasts.models import Artist, EpisodeSong, PodcastLink
from podcasts.models.episode_chapter import EpisodeChapter
from podcasts.widgets import ArtistAutocompleteWidget
from utils.admin_mixin import AdminMixin


class ArtistSongInline(AdminMixin, admin.TabularInline):
    extra = 0
    fields = ["song", "episode"]
    model = EpisodeSong.artists.through
    readonly_fields = ["song", "episode"]
    verbose_name = "song"
    verbose_name_plural = "songs"

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


class EpisodeSongInline(AdminMixin, admin.TabularInline):
    autocomplete_fields = ["artists"]
    fields = ["episode", "start_time", "end_time", "title", "artists", "comment", "url", "image"]
    model = EpisodeSong
    extra = 1

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "artists":
            kwargs["queryset"] = Artist.objects.all()
            kwargs["widget"] = ArtistAutocompleteWidget(
                field=db_field,
                admin_site=self.admin_site,
                using=kwargs.get("using"),
            )
            kwargs["required"] = False
            return ArtistMultipleChoiceField(**kwargs)

        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("artists")


class EpisodeChapterInline(AdminMixin, admin.TabularInline):
    model = EpisodeChapter
    extra = 1
    fields = ["episode", "start_time", "end_time", "title", "url", "image"]


class PodcastLinkInline(AdminMixin, admin.TabularInline):
    model = PodcastLink
    extra = 0
