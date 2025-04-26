import logging
import os
import tempfile
from datetime import timedelta
from functools import update_wrapper
from threading import Thread

from django.contrib import admin
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.core.files import File
from django.core.files.uploadedfile import UploadedFile
from django.db import models
from django.db.models import Count, F, OuterRef, Q, Subquery
from django.http import HttpRequest, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.safestring import mark_safe
from martor.models import MartorField
from pydub import AudioSegment
from pydub.utils import mediainfo

from logs.models import (
    PodcastContentRequestLog,
    PodcastEpisodeAudioRequestLog,
    PodcastRequestLog,
)
from podcasts.admin_filters import ArtistSongCountFilter
from podcasts.admin_inlines import (
    ArtistSongInline,
    EpisodeSongInline,
    PodcastLinkInline,
)
from podcasts.forms import EpisodeSongForm, PodcastChangeSlugForm
from podcasts.models import (
    Artist,
    Comment,
    Episode,
    EpisodeSong,
    Podcast,
    Post,
)
from utils import (
    delete_storage_file,
    get_audio_segment_dbfs_array,
    seconds_to_timestamp,
)
from utils.admin_mixin import AdminMixin
from utils.widgets import AdminMartorWidget


logger = logging.getLogger(__name__)


@admin.register(Podcast)
class PodcastAdmin(AdminMixin, admin.ModelAdmin):
    add_fields = (
        ("name", "slug"),
        "tagline",
        ("cover", "banner"),
        "favicon",
        "language",
        "description",
        "categories",
    )
    fields = (
        ("name", "slug"),
        "tagline",
        ("cover", "banner"),
        "favicon",
        "language",
        ("name_font_family", "name_font_size"),
        ("enable_comments", "require_comment_approval"),
        "owner",
        "description",
        "categories",
        "authors",
    )
    filter_horizontal = ["categories", "authors"]
    formfield_overrides = {
        MartorField: {"widget": AdminMartorWidget},
    }
    inlines = [PodcastLinkInline]
    list_display = (
        "name",
        "slug",
        "owner_link",
        "author_links",
        "view_count",
        "total_view_count",
        "play_count",
        "play_time",
        "frontend_link",
    )
    readonly_fields = ("slug",)
    save_on_top = True

    @admin.display(description="authors")
    def author_links(self, obj: Podcast):
        return mark_safe("<br>".join(u.get_admin_link() for u in obj.authors.all()))

    def change_slug_view(self, request: HttpRequest, object_id):
        obj = self.get_object(request, unquote(object_id))

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            return self._get_obj_does_not_exist_redirect(request, self.opts, object_id)

        if request.method == "POST":
            form = PodcastChangeSlugForm(request.POST, instance=obj)
            if form.is_valid():
                form.save(commit=True)
                self.message_user(request, "The slug was changed.")
                return HttpResponseRedirect(
                    add_preserved_filters(
                        {
                            "preserved_filters": self.get_preserved_filters(request),
                            "opts": self.opts,
                        },
                        reverse(
                            f"admin:{self.opts.app_label}_{self.opts.model_name}_changelist",
                            current_app=self.admin_site.name,
                        ),
                    )
                )
        else:
            form = PodcastChangeSlugForm(instance=obj)

        return TemplateResponse(
            request=request,
            template=f"admin/{self.opts.app_label}/{self.opts.model_name}/change_slug.html",
            context={
                "opts": self.opts,
                "form": form,
            },
        )

    def frontend_link(self, obj: Podcast):
        return mark_safe(f'<a href="{obj.frontend_url}" target="_blank">{obj.frontend_url}</a>')

    def get_fields(self, request, obj=None):
        if obj:
            return self.fields
        return self.add_fields

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .prefetch_related("authors")
            .select_related("owner")
            .alias(content_view_count=Count("contents__requests", distinct=True))
            .annotate(
                view_count=Count("requests", distinct=True),
                total_view_count=F("content_view_count") + F("view_count"),
                play_count=Subquery(
                    PodcastEpisodeAudioRequestLog.objects
                    .filter(is_bot=False)
                    .get_play_count_query(episode__podcast=OuterRef("slug"))
                ),
                play_time=Subquery(
                    PodcastEpisodeAudioRequestLog.objects
                    .filter(is_bot=False)
                    .get_play_time_query(episode__podcast=OuterRef("slug"))
                ),
            )
        )

    def get_urls(self):
        from django.urls import path

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)

            setattr(wrapper, "model_admin", self)
            return update_wrapper(wrapper, view)

        return [
            path(
                "<path:object_id>/change_slug/",
                wrap(self.change_slug_view),
                name=f"{self.opts.app_label}_{self.opts.model_name}_change_slug",
            ),
        ] + super().get_urls()

    @admin.display(description="owner")
    def owner_link(self, obj: Podcast):
        return obj.owner.get_admin_link()

    @admin.display(description="plays", ordering="play_count")
    def play_count(self, obj):
        if obj.play_count is None:
            return 0.0

        return PodcastEpisodeAudioRequestLog.get_admin_list_link(
            text=round(obj.play_count, 2),
            episode__podcast__slug__exact=obj.pk,
            is_bot__exact=0,
        )

    @admin.display(description="play time", ordering="play_time")
    def play_time(self, obj):
        if obj.play_time is None:
            return timedelta()

        return PodcastEpisodeAudioRequestLog.get_admin_list_link(
            text=obj.play_time,
            episode__podcast__slug__exact=obj.pk,
            is_bot__exact=0,
        )

    def save_form(self, request, form, change):
        instance: Podcast = super().save_form(request, form, change)

        if not change:
            instance.authors.add(request.user)
            instance.owner = request.user
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

    @admin.display(description="views recursive", ordering="total_view_count")
    def total_view_count(self, obj):
        return obj.total_view_count

    @admin.display(description="views", ordering="view_count")
    def view_count(self, obj):
        if not obj.view_count:
            return 0

        return PodcastRequestLog.get_admin_list_link(text=obj.view_count, podcast__slug__exact=obj.pk)


class BasePodcastContentAdmin(AdminMixin, admin.ModelAdmin):
    formfield_overrides = {
        MartorField: {"widget": AdminMartorWidget},
    }
    save_on_top = True
    search_fields = ["name", "description", "slug"]

    def get_form(self, request, obj=None, change=False, **kwargs):
        Form = super().get_form(request, obj, change, **kwargs)
        field = Form.base_fields.get("podcast")
        if field and not request.user.is_superuser:
            field.queryset = field.queryset.filter(Q(authors=request.user) | Q(owner=request.user)).distinct()
        return Form

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related("podcast", "podcast__owner")
            .prefetch_related("podcast__authors")
            .annotate(view_count=Count("requests", distinct=True))
        )


@admin.register(Episode)
class EpisodeAdmin(BasePodcastContentAdmin):
    fields = (
        ("podcast", "slug"),
        ("season", "number"),
        "name",
        ("is_draft", "published"),
        "audio_file",
        "image",
        "description",
        "duration",
        "audio_content_type",
        "audio_file_length",
    )
    inlines = [EpisodeSongInline]
    list_display = (
        "name",
        "season",
        "number",
        "is_visible",
        "is_draft",
        "podcast_link",
        "published",
        "view_count",
        "play_count",
        "play_time",
    )
    list_filter = ["is_draft", "published", "podcast"]
    readonly_fields = ("audio_content_type", "audio_file_length", "slug", "duration")
    search_fields = ["name", "description", "slug", "songs__name", "songs__artists__name"]

    def duration(self, obj: Episode):
        return timedelta(seconds=int(obj.duration_seconds))

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .annotate(
                play_count=Subquery(
                    PodcastEpisodeAudioRequestLog.objects
                    .filter(is_bot=False)
                    .get_play_count_query(episode=OuterRef("pk"))
                ),
                play_time=Subquery(
                    PodcastEpisodeAudioRequestLog.objects
                    .filter(is_bot=False)
                    .get_play_time_query(episode=OuterRef("pk"))
                )
            )
        )

    def handle_audio_file_async(self, instance: Episode, audio_file: UploadedFile):
        stem, extension = os.path.splitext(os.path.basename(audio_file.name))
        suffix = extension.strip(".")
        update_fields = ["dbfs_array", "duration_seconds"]

        with tempfile.NamedTemporaryFile(suffix=suffix) as temp_file:
            temp_stem, _ = os.path.splitext(temp_file.name)
            temp_file.write(audio_file.read())
            temp_file.seek(0)

            info = mediainfo(temp_file.name)
            instance.duration_seconds = float(info["duration"])
            audio: AudioSegment = AudioSegment.from_file(temp_file, info["format_name"])
            max_dbfs = audio.max_dBFS

            if max_dbfs < 0:
                dbfs = audio.dBFS
                if dbfs < -14:
                    gain = min(-max_dbfs, -dbfs - 14)
                    logger.info("Applying %f dBFS gain to %s", gain, instance)
                    audio = audio.apply_gain(gain)

                    with audio.export(
                        temp_stem + ".mp3",
                        format="mp3",
                        bitrate="192k",
                        tags=info.get("TAG"),
                    ) as new_file:
                        delete_storage_file(instance.audio_file)
                        instance.audio_file.save(name=stem + ".mp3", content=File(new_file), save=False)
                        new_file.seek(0)
                        instance.audio_content_type = "audio/mpeg"
                        instance.audio_file_length = len(new_file.read())
                        update_fields.extend(["audio_file", "audio_content_type", "audio_file_length"])

        instance.dbfs_array = get_audio_segment_dbfs_array(audio)
        instance.save(update_fields=update_fields)

        logger.info("handle_audio_file_async finished for %s", instance)

    @admin.display(description="plays", ordering="play_count")
    def play_count(self, obj):
        if obj.play_count is None:
            return 0.0

        return PodcastEpisodeAudioRequestLog.get_admin_list_link(
            text=round(obj.play_count, 2),
            episode__podcastcontent_ptr__exact=obj.pk,
            is_bot__exact=0,
        )

    @admin.display(description="play time", ordering="play_time")
    def play_time(self, obj):
        if obj.play_time is None:
            return timedelta()

        return PodcastEpisodeAudioRequestLog.get_admin_list_link(
            text=obj.play_time,
            episode__podcastcontent_ptr__exact=obj.pk,
            is_bot__exact=0,
        )

    @admin.display(description="podcast", ordering="podcast")
    def podcast_link(self, obj: Episode):
        return obj.podcast.get_admin_link()

    def save_form(self, request, form, change):
        instance: Episode = super().save_form(request, form, change)

        if "image" in form.changed_data:
            if "image" in form.initial:
                delete_storage_file(form.initial["image"])
            instance.handle_uploaded_image()
        if "audio_file" in form.changed_data:
            if "audio_file" in form.initial:
                delete_storage_file(form.initial["audio_file"])
            if form.cleaned_data["audio_file"]:
                audio_file: UploadedFile = form.cleaned_data["audio_file"]
                instance.audio_content_type = audio_file.content_type
                instance.audio_file_length = audio_file.size
            else:
                instance.duration_seconds = 0.0
                instance.audio_content_type = ""
                instance.audio_file_length = 0
                instance.dbfs_array = []

        logger.info("save_form finished for %s with audio_file=%s", instance, instance.audio_file)
        return instance

    def save_model(self, request, obj: Episode, form, change):
        super().save_model(request, obj, form, change)

        if "audio_file" in form.changed_data and form.cleaned_data["audio_file"]:
            Thread(
                target=self.handle_audio_file_async,
                kwargs={"audio_file": form.cleaned_data["audio_file"], "instance": obj},
            ).start()

    @admin.display(description="views", ordering="view_count")
    def view_count(self, obj):
        if not obj.view_count:
            return 0

        return PodcastContentRequestLog.get_admin_list_link(text=obj.view_count, content__id__exact=obj.pk)


@admin.register(Post)
class PostAdmin(BasePodcastContentAdmin):
    fields = (
        "podcast",
        "name",
        ("is_draft", "published"),
        "description",
    )
    list_display = ("name", "is_visible", "is_draft", "podcast", "published")


@admin.register(Artist)
class ArtistAdmin(AdminMixin, admin.ModelAdmin):
    inlines = [ArtistSongInline]
    list_display = ["name", "song_count"]
    list_filter = [ArtistSongCountFilter]
    save_on_top = True
    search_fields = ["name"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(song_count=models.Count("songs"))

    @admin.display(description="songs", ordering="song_count")
    def song_count(self, obj):
        return obj.song_count


@admin.register(EpisodeSong)
class EpisodeSongAdmin(AdminMixin, admin.ModelAdmin):
    filter_horizontal = ["artists"]
    form = EpisodeSongForm
    list_display = ["name", "artists_str", "episode_str", "timestamp_str"]
    ordering = ["-episode__number", "timestamp"]
    save_on_top = True
    search_fields = ["name", "artists__name", "comment"]

    @admin.display(description="artists")
    def artists_str(self, obj: EpisodeSong):
        return mark_safe("<br>".join(a.get_admin_link(text=a.name) for a in obj.artists.all()))

    @admin.display(description="episode", ordering="episode__number")
    def episode_str(self, obj: EpisodeSong):
        return obj.episode.get_admin_link()

    def get_form(self, request, obj=None, change=False, **kwargs):
        Form = super().get_form(request, obj, change, **kwargs)
        field = Form.base_fields.get("episode")
        if field:
            field.queryset = (
                field.queryset
                .filter(Q(podcast__authors=request.user) | Q(podcast__owner=request.user))
                .distinct()
            )
        return Form

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .prefetch_related("artists", "episode__podcast__authors")
            .select_related("episode__podcast__owner")
        )

    @admin.display(description="timestamp", ordering="timestamp")
    def timestamp_str(self, obj: EpisodeSong):
        return seconds_to_timestamp(obj.timestamp)


@admin.action(description="Approve comments")
def approve_comments(modeladmin, request, queryset):
    queryset.update(is_approved=True)


@admin.register(Comment)
class CommentAdmin(AdminMixin, admin.ModelAdmin):
    actions = [approve_comments]
    list_display = ["name", "truncated_text", "created", "is_approved", "content_link"]
    list_filter = ["is_approved", "podcast_content__podcast"]
    readonly_fields = ["podcast_content", "name", "text"]

    @admin.display(description="content")
    def content_link(self, obj: Comment):
        return obj.podcast_content.get_real_instance().get_admin_link()

    def get_form(self, request, obj=None, change=False, **kwargs):
        Form = super().get_form(request, obj, change, **kwargs)
        field = Form.base_fields.get("podcast_content")
        if field:
            field.queryset = (
                field.queryset
                .filter(Q(podcast__authors=request.user) | Q(podcast__owner=request.user))
                .distinct()
            )
        return Form

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .prefetch_related("podcast_content__podcast__authors")
            .select_related("podcast_content__podcast__owner")
        )

    @admin.display(description="text")
    def truncated_text(self, obj: Comment):
        if len(obj.text) > 1000:
            return obj.text[:1000] + "..."
        return obj.text
