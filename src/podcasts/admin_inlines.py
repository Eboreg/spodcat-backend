from django.contrib import admin

from podcasts.fields import ArtistMultipleChoiceField
from podcasts.forms import EpisodeSongForm
from podcasts.models import Artist, EpisodeSong, PodcastLink
from podcasts.widgets import ArtistAutocompleteWidget


class ArtistSongInline(admin.TabularInline):
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
        return obj.episodesong.name


class EpisodeSongInline(admin.TabularInline):
    autocomplete_fields = ["artists"]
    fields = ["episode", "timestamp", "name", "artists", "comment"]
    form = EpisodeSongForm
    model = EpisodeSong

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

    def get_extra(self, request, obj=None, **kwargs):
        if obj is None:
            return 10
        return 3

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("artists")


class PodcastLinkInline(admin.TabularInline):
    model = PodcastLink
    extra = 0
