import tempfile
from threading import Thread
from typing import BinaryIO

from django.contrib import admin
from django.core.files.uploadedfile import UploadedFile
from django.db import models
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from martor.models import MartorField
from pydub.utils import mediainfo

from podcasts.fields import (
    AdminMartorWidget,
    ArtistAutocompleteWidget,
    ArtistMultipleChoiceField,
    EpisodeSongForm,
    seconds_to_timestamp,
)
from podcasts.models import (
    Artist,
    Episode,
    EpisodeSong,
    Podcast,
    PodcastLink,
    Post,
)
from podcasts.utils import delete_storage_file


class PodcastLinkInline(admin.TabularInline):
    model = PodcastLink
    extra = 0


@admin.register(Podcast)
class PodcastAdmin(admin.ModelAdmin):
    filter_horizontal = ["categories", "owners"]
    fields = (
        ("name", "slug"),
        "tagline",
        ("cover", "banner"),
        "favicon",
        "language",
        "description",
        "categories",
        "owners",
    )
    formfield_overrides = {
        MartorField: {"widget": AdminMartorWidget},
    }
    inlines = [PodcastLinkInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("owners")

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or obj is None or request.user in obj.owners.all()

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def save_form(self, request, form, change):
        instance: Podcast = super().save_form(request, form, change)

        if "cover" in form.changed_data:
            if "cover" in form.initial:
                delete_storage_file(form.initial["cover"])
            instance.handle_uploaded_cover()
        if "banner" in form.changed_data:
            if "banner" in form.initial:
                delete_storage_file(form.initial["banner"])
            instance.handle_uploaded_banner()
        if "favicon" in form.changed_data:
            if "favicon" in form.initial:
                delete_storage_file(form.initial["favicon"])
            if form.cleaned_data["favicon"]:
                instance.favicon_content_type = form.cleaned_data["favicon"].content_type
            else:
                instance.favicon_content_type = None
            instance.handle_uploaded_favicon()

        return instance


class EpisodeSongInline(admin.TabularInline):
    model = EpisodeSong
    autocomplete_fields = ["artists"]
    form = EpisodeSongForm
    fields = ["episode", "timestamp", "name", "artists", "comment"]

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


class BasePodcastContentAdmin(admin.ModelAdmin):
    formfield_overrides = {
        MartorField: {"widget": AdminMartorWidget},
    }

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or obj is None or request.user in obj.podcast.owners.all()

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def get_form(self, request, obj=None, change=False, **kwargs):
        Form = super().get_form(request, obj, change, **kwargs)
        field = Form.base_fields.get("podcast")
        if field:
            field.queryset = field.queryset.filter(owners=request.user)
        return Form

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("podcast").prefetch_related("podcast__owners")


@admin.register(Episode)
class EpisodeAdmin(BasePodcastContentAdmin):
    list_display = ("name", "number", "is_published", "is_draft", "podcast_str", "published")
    fields = (
        ("podcast", "slug"),
        ("number", "name"),
        ("is_draft", "published"),
        "audio_file",
        "description",
        "duration_seconds",
        "audio_content_type",
        "audio_file_length",
    )
    readonly_fields = ("duration_seconds", "audio_content_type", "audio_file_length", "slug")
    inlines = [EpisodeSongInline]
    list_filter = ["is_draft", "published", "podcast"]

    @admin.display(description="podcast", ordering="podcast")
    def podcast_str(self, obj: Episode):
        return format_html(
            "<a href=\"{url}\">{name}</a>",
            url=reverse("admin:podcasts_podcast_change", args=(obj.podcast.pk,)),
            name=str(obj.podcast),
        )

    def handle_audio_file(self, instance: Episode, audio_file: UploadedFile):
        suffix = "." + audio_file.name.split(".")[-1]

        # pylint: disable=consider-using-with
        file = tempfile.NamedTemporaryFile(suffix=suffix)
        file.write(audio_file.read())
        file.seek(0)

        info = mediainfo(file.name)
        instance.duration_seconds = float(info["duration"])
        instance.audio_content_type = audio_file.content_type
        instance.audio_file_length = audio_file.size

        Thread(
            target=self.update_audio_file_dbfs_array,
            kwargs={"file": file, "format_name": info["format_name"], "instance": instance},
        ).start()

    def save_form(self, request, form, change):
        instance: Episode = super().save_form(request, form, change)

        if "audio_file" in form.changed_data:
            if "audio_file" in form.initial:
                delete_storage_file(form.initial["audio_file"])
            if form.cleaned_data["audio_file"]:
                self.handle_audio_file(instance, form.cleaned_data["audio_file"])
            else:
                instance.duration_seconds = 0.0
                instance.audio_content_type = ""
                instance.audio_file_length = 0
                instance.dbfs_array = []

        return instance

    def update_audio_file_dbfs_array(self, instance: Episode, file: BinaryIO, format_name: str):
        instance.update_audio_file_dbfs_array(file=file, format_name=format_name, save=True)
        file.close()
        print("update_audio_file_dbfs_array finished")


@admin.register(Post)
class PostAdmin(BasePodcastContentAdmin):
    list_display = ("name", "is_published", "is_draft", "podcast", "published")
    fields = (
        "podcast",
        "name",
        ("is_draft", "published"),
        "description",
    )


class ArtistSongCountFilter(admin.SimpleListFilter):
    title = "song count"
    parameter_name = "song_count"

    def lookups(self, request, model_admin):
        return [
            ("0", "0"),
            ("1", "1"),
            ("2-10", "2-10"),
            ("10-", "10+"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "0":
            return queryset.filter(song_count=0)
        if self.value() == "1":
            return queryset.filter(song_count=1)
        if self.value() == "2-10":
            return queryset.filter(song_count__gte=2, song_count__lte=10)
        if self.value() == "10-":
            return queryset.filter(song_count__gt=10)
        return queryset


class ArtistSongInline(admin.TabularInline):
    model = EpisodeSong.artists.through
    extra = 0
    fields = ["song", "episode"]
    readonly_fields = ["song", "episode"]
    verbose_name = "song"
    verbose_name_plural = "songs"

    def episode(self, obj):
        return obj.episodesong.episode

    def song(self, obj):
        return obj.episodesong.name

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("episodesong__episode")

    def has_add_permission(self, request, obj):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_display = ["name", "song_count"]
    list_filter = [ArtistSongCountFilter]
    inlines = [ArtistSongInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(song_count=models.Count("songs"))

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser or obj is None:
            return True
        return not Podcast.objects.filter(contents__episode__songs__artists=obj).exclude(owners=request.user).exists()

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    @admin.display(description="songs", ordering="song_count")
    def song_count(self, obj):
        return obj.song_count


@admin.register(EpisodeSong)
class EpisodeSongAdmin(admin.ModelAdmin):
    list_display = ["name", "artists_str", "episode_str", "timestamp_str"]
    ordering = ["-episode__number", "timestamp"]
    search_fields = ["name", "artists__name", "comment"]
    filter_horizontal = ["artists"]
    form = EpisodeSongForm

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("artists", "episode__podcast__owners")

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or obj is None or request.user in obj.episode.podcast.owners.all()

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def get_form(self, request, obj=None, change=False, **kwargs):
        Form = super().get_form(request, obj, change, **kwargs)
        field = Form.base_fields.get("episode")
        if field:
            field.queryset = field.queryset.filter(podcast__owners=request.user)
        return Form

    @admin.display(description="episode", ordering="episode__number")
    def episode_str(self, obj: EpisodeSong):
        return format_html(
            "<a href=\"{url}\">{name}</a>",
            url=reverse("admin:podcasts_episode_change", args=(obj.episode.pk,)),
            name=str(obj.episode),
        )

    @admin.display(description="artists")
    def artists_str(self, obj: EpisodeSong):
        return mark_safe(
            "<br>".join(
                format_html(
                    "<a href=\"{url}\">{name}</a>",
                    url=reverse("admin:podcasts_artist_change", args=(a.pk,)),
                    name=a.name,
                ) for a in obj.artists.all()
            )
        )

    @admin.display(description="timestamp", ordering="timestamp")
    def timestamp_str(self, obj: EpisodeSong):
        return seconds_to_timestamp(obj.timestamp)
