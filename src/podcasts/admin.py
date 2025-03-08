import tempfile
from io import BytesIO
from threading import Thread
from typing import BinaryIO

from django.contrib import admin
from django.core.files.images import ImageFile
from django.core.files.uploadedfile import UploadedFile
from django.db import models
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from martor.widgets import AdminMartorWidget
from PIL import Image
from pydub.utils import mediainfo

from podcasts.fields import (
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
    )
    formfield_overrides = {
        models.TextField: {"widget": AdminMartorWidget},
    }
    inlines = [PodcastLinkInline]

    def handle_banner(self, instance: Podcast):
        if instance.banner and instance.banner.width > 960 and instance.banner.height > 320:
            ratio = max(960 / instance.banner.width, 320 / instance.banner.height)
            buf = BytesIO()

            with Image.open(instance.banner) as im:
                im.thumbnail((int(instance.banner.width * ratio), int(instance.banner.height * ratio)))
                im.save(buf, format=im.format)

            instance.banner.save(name=instance.banner.name, content=buf, save=False)

    def handle_cover(self, instance: Podcast):
        if instance.cover:
            stem, suffix = instance.cover.name.rsplit(".", maxsplit=1)
            filename = f"{stem}-thumbnail.{suffix}"
            buf = BytesIO()

            with Image.open(instance.cover) as im:
                ratio = 150 / max(im.width, im.height)
                im.thumbnail((int(im.width * ratio), int(im.height * ratio)))
                im.save(buf, format=im.format)

            instance.cover_mimetype = im.get_format_mimetype()
            instance.cover_thumbnail_mimetype = im.get_format_mimetype()
            instance.cover_thumbnail.save(name=filename, content=ImageFile(file=buf), save=False)

        else:
            instance.cover_thumbnail.delete(save=False)
            instance.cover_mimetype = None
            instance.cover_thumbnail_mimetype = None

    def handle_favicon(self, instance: Podcast, file: UploadedFile | None):
        if file:
            instance.favicon_content_type = file.content_type

        if instance.favicon:
            if instance.favicon.width > 100 and instance.favicon.height > 100:
                ratio = max(100 / instance.favicon.width, 100 / instance.favicon.height)
                buf = BytesIO()

                with Image.open(instance.favicon) as im:
                    im.thumbnail((int(instance.favicon.width * ratio), int(instance.favicon.height * ratio)))
                    im.save(buf, format=im.format)

                instance.favicon.save(name=instance.favicon.name, content=buf, save=False)
        else:
            instance.favicon_content_type = None

    def save_form(self, request, form, change):
        instance: Podcast = super().save_form(request, form, change)

        if "cover" in form.changed_data:
            self.handle_cover(instance)

        if "banner" in form.changed_data:
            self.handle_banner(instance)

        if "favicon" in form.changed_data:
            self.handle_favicon(instance, form.cleaned_data["favicon"])

        return instance


class EpisodeSongInline(admin.TabularInline):
    model = EpisodeSong
    autocomplete_fields = ["artists"]
    form = EpisodeSongForm
    fields = ["episode", "name", "timestamp", "artists", "comment"]

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


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = ("name", "number", "is_published", "is_draft", "podcast_str", "published")
    formfield_overrides = {
        models.TextField: {"widget": AdminMartorWidget},
    }
    fields = (
        "podcast",
        ("number", "name"),
        ("is_draft", "published"),
        "audio_file",
        "description",
        "duration_seconds",
        "audio_content_type",
        "audio_file_length",
    )
    readonly_fields = ("duration_seconds", "audio_content_type", "audio_file_length")
    inlines = [EpisodeSongInline]
    list_filter = ["is_draft", "published", "podcast"]

    class Media:
        js = ["assets/js/episode_song.js"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("podcast")

    @admin.display(description="podcast", ordering="podcast")
    def podcast_str(self, obj: Episode):
        return format_html(
            "<a href=\"{url}\">{name}</a>",
            url=reverse("admin:podcasts_podcast_change", args=(obj.podcast.pk,)),
            name=str(obj.podcast),
        )

    def save_form(self, request, form, change):
        instance: Episode = super().save_form(request, form, change)

        if "audio_file" in form.changed_data:
            audio_file: UploadedFile = form.cleaned_data["audio_file"]
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

        return instance

    def update_audio_file_dbfs_array(self, instance: Episode, file: BinaryIO, format_name: str):
        instance.update_audio_file_dbfs_array(file=file, format_name=format_name, save=True)
        file.close()


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("name", "is_published", "is_draft", "podcast", "published")
    formfield_overrides = {
        models.TextField: {"widget": AdminMartorWidget},
    }
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


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_display = ["name", "song_count"]
    list_filter = [ArtistSongCountFilter]
    inlines = [ArtistSongInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(song_count=models.Count("songs"))

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
        return super().get_queryset(request).prefetch_related("artists").select_related("episode")

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
