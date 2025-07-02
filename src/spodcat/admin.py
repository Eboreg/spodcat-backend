import logging
import os
import tempfile
from datetime import timedelta
from functools import update_wrapper
from threading import Thread
from typing import Any

from django.apps import apps
from django.contrib import admin
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.core.files import File
from django.core.files.uploadedfile import UploadedFile
from django.db import models
from django.db.models import Count, F, OuterRef, Q, Subquery
from django.forms import ModelChoiceField
from django.http import HttpRequest, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from pydub import AudioSegment

from spodcat.admin_inlines import (
    ArtistSongInline,
    EpisodeChapterInline,
    EpisodeSongInline,
    PodcastLinkInline,
)
from spodcat.contrib.admin.filters import ArtistSongCountFilter
from spodcat.contrib.admin.mixin import AdminMixin
from spodcat.forms import PodcastChangeSlugForm
from spodcat.models import Artist, Comment, Episode, EpisodeSong, Podcast, Post
from spodcat.utils import delete_storage_file, seconds_to_timestamp


logger = logging.getLogger(__name__)


@admin.register(Podcast)
class PodcastAdmin(AdminMixin, admin.ModelAdmin):
    add_fields = (
        ("name", "slug"),
        "tagline",
        ("cover", "banner"),
        "favicon",
        "language",
        ("name_font_family", "name_font_size"),
        ("enable_comments", "require_comment_approval"),
        "custom_guid",
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
        "custom_guid",
        "owner",
        "description",
        "categories",
        "authors",
    )
    filter_horizontal = ["categories", "authors"]
    inlines = [PodcastLinkInline]
    readonly_fields = ("slug",)
    save_on_top = True

    def get_list_display(self, request):
        if apps.is_installed("spodcat.logs"):
            return (
                "name",
                "slug",
                "owner_link",
                "author_links",
                "view_count",
                "total_view_count",
                "play_count",
                "player_count",
                "play_time",
                "frontend_link",
            )
        return ("name", "slug", "owner_link", "author_links", "frontend_link")

    @admin.display(description=_("authors"))
    def author_links(self, obj: Podcast):
        return mark_safe("<br>".join(self.get_change_link(u) for u in obj.authors.all()))

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
                self.message_user(request, _("The slug was changed."))
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
        qs = super().get_queryset(request).prefetch_related("authors").select_related("owner")

        if apps.is_installed("spodcat.logs"):
            from spodcat.logs.models import PodcastEpisodeAudioRequestLog

            return (
                qs
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
                    player_count=Subquery(
                        PodcastEpisodeAudioRequestLog.objects
                        .filter(is_bot=False, response_body_size__gt=0, episode__podcast=OuterRef("slug"))
                        .order_by()
                        .values("episode__podcast")
                        .annotate(player_count=Count("remote_addr", distinct=True))
                        .values("player_count")
                    )
                )
            )

        return qs

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

    @admin.display(description=_("owner"))
    def owner_link(self, obj: Podcast):
        return self.get_change_link(obj.owner)

    @admin.display(description=_("plays"), ordering="play_count")
    def play_count(self, obj):
        from spodcat.logs.models import PodcastEpisodeAudioRequestLog

        if obj.play_count is None:
            return 0.0

        return self.get_changelist_link(
            model=PodcastEpisodeAudioRequestLog,
            text=round(obj.play_count, 2),
            episode__podcast__slug__exact=obj.pk,
            is_bot__exact=0,
        )

    @admin.display(description=_("play time"), ordering="play_time")
    def play_time(self, obj):
        play_time = obj.play_time or timedelta()
        return timedelta(seconds=round(play_time.total_seconds()))

    @admin.display(description=_("players"), ordering="player_count")
    def player_count(self, obj):
        return obj.player_count

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

    @admin.display(description=_("views recursive"), ordering="total_view_count")
    def total_view_count(self, obj):
        return obj.total_view_count

    @admin.display(description=_("views"), ordering="view_count")
    def view_count(self, obj):
        from spodcat.logs.models import PodcastRequestLog

        if not obj.view_count:
            return 0

        return self.get_changelist_link(
            model=PodcastRequestLog,
            text=obj.view_count,
            podcast__slug__exact=obj.pk,
        )


class BasePodcastContentAdmin(AdminMixin, admin.ModelAdmin):
    save_on_top = True
    search_fields = ["name", "description", "slug"]

    def get_form(self, request, obj=None, change=False, **kwargs):
        Form = super().get_form(request, obj, change, **kwargs)
        field = Form.base_fields.get("podcast")
        if isinstance(field, ModelChoiceField) and not request.user.is_superuser:
            field.queryset = field.queryset.filter(Q(authors=request.user) | Q(owner=request.user)).distinct()
        return Form

    def get_queryset(self, request):
        qs = (
            super().get_queryset(request)
            .select_related("podcast", "podcast__owner")
            .prefetch_related("podcast__authors")
        )

        if apps.is_installed("spodcat.logs"):
            return (
                qs
                .annotate(view_count=Count("requests", distinct=True))
                .annotate(visitor_count=Count("requests__remote_addr", distinct=True))
            )

        return qs

    @admin.display(description=_("views"), ordering="view_count")
    def view_count(self, obj):
        from spodcat.logs.models import PodcastContentRequestLog

        if not obj.view_count:
            return 0

        return self.get_changelist_link(
            model=PodcastContentRequestLog,
            text=obj.view_count,
            content__id__exact=obj.pk,
        )

    @admin.display(description=_("visitors"), ordering="visitor_count")
    def visitor_count(self, obj):
        return obj.visitor_count


@admin.register(Episode)
class EpisodeAdmin(BasePodcastContentAdmin):
    fields = (
        ("id", "slug"),
        ("podcast", "name"),
        ("season", "number"),
        ("is_draft", "published"),
        "audio_file",
        "image",
        "description",
        "duration",
        "audio_content_type",
        "audio_file_length",
    )
    inlines = [EpisodeSongInline, EpisodeChapterInline]
    list_display = (
        "name",
        "season",
        "number_string",
        "is_visible",
        "is_draft",
        "podcast_link",
        "published",
        "view_count",
        "visitor_count",
        "play_count",
        "player_count",
        "play_time",
        "frontend_link",
    )
    list_filter = ["is_draft", "published", "podcast"]
    readonly_fields = ("audio_content_type", "audio_file_length", "slug", "duration", "id")
    search_fields = ["name", "description", "slug", "songs__title", "songs__artists__name"]

    def get_list_display(self, request):
        if apps.is_installed("spodcat.logs"):
            return (
                "name",
                "season",
                "number_string",
                "is_visible",
                "is_draft",
                "podcast_link",
                "published",
                "view_count",
                "visitor_count",
                "play_count",
                "player_count",
                "play_time",
                "frontend_link",
            )
        return (
            "name",
            "season",
            "number_string",
            "is_visible",
            "is_draft",
            "podcast_link",
            "published",
            "frontend_link",
        )

    def apply_gain(self, instance: Episode, audio: AudioSegment, stem: str, tags: Any, save: bool = True) -> bool:
        max_dbfs = audio.max_dBFS

        if max_dbfs < 0:
            dbfs = audio.dBFS
            if dbfs < -14:
                gain = min(-max_dbfs, -dbfs - 14)
                logger.info("Applying %f dBFS gain to %s", gain, instance)
                audio = audio.apply_gain(gain)

                with audio.export(stem + ".mp3", format="mp3", bitrate="192k", tags=tags) as new_file:
                    delete_storage_file(instance.audio_file)
                    instance.audio_file.save(name=stem + ".mp3", content=File(new_file), save=False)
                    new_file.seek(0)
                    instance.audio_content_type = "audio/mpeg"
                    instance.audio_file_length = len(new_file.read())

                if save:
                    instance.save(update_fields=["audio_file", "audio_content_type", "audio_file_length"])

                return True

        return False

    def duration(self, obj: Episode):
        return timedelta(seconds=int(obj.duration_seconds))

    def frontend_link(self, obj: Episode):
        return mark_safe(f'<a href="{obj.frontend_url}" target="_blank">' + _("Link") + "</a>")

    def get_queryset(self, request):
        if apps.is_installed("spodcat.logs"):
            from spodcat.logs.models import PodcastEpisodeAudioRequestLog

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
                    ),
                    player_count=Count(
                        "audio_requests__remote_addr",
                        distinct=True,
                        filter=Q(audio_requests__is_bot=False, audio_requests__response_body_size__gt=0),
                    ),
                )
            )

        return super().get_queryset(request)

    def handle_audio_file_async(self, instance: Episode, temp_file: tempfile._TemporaryFileWrapper):
        logger.info("handle_audio_file_async starting for %s, temp_file=%s", instance, temp_file)

        try:
            instance.get_dbfs_and_duration(temp_file=temp_file)
            # Skipping the applying of gain, but here is how to use it:
            # temp_stem, _ = os.path.splitext(temp_file.name)
            # if self.apply_gain(instance=instance, audio=audio, stem=temp_stem, tags=info.get("TAG"), save=False):
            #     update_fields.extend(["audio_file", "audio_content_type", "audio_file_length"])
            logger.info("handle_audio_file_async finished for %s", instance)
        except Exception as e:
            logger.error("handle_audio_file_async error", exc_info=e)

    @admin.display(description=_("number"), ordering="number")
    def number_string(self, obj: Episode):
        return obj.number_string

    @admin.display(description=_("plays"), ordering="play_count")
    def play_count(self, obj):
        from spodcat.logs.models import PodcastEpisodeAudioRequestLog

        if obj.play_count is None:
            return 0.0

        return self.get_changelist_link(
            model=PodcastEpisodeAudioRequestLog,
            text=round(obj.play_count, 2),
            episode__podcastcontent_ptr__exact=obj.pk,
            is_bot__exact=0,
        )

    @admin.display(description=_("play time"), ordering="play_time")
    def play_time(self, obj):
        play_time = obj.play_time if obj.play_time is not None else timedelta()
        return timedelta(seconds=round(play_time.total_seconds()))

    @admin.display(description=_("players"), ordering="player_count")
    def player_count(self, obj):
        return obj.player_count

    @admin.display(description=_("podcast"), ordering="podcast")
    def podcast_link(self, obj: Episode):
        return self.get_change_link(obj.podcast)

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
            audio_file: UploadedFile = form.cleaned_data["audio_file"]
            _, extension = os.path.splitext(os.path.basename(audio_file.name))

            # Cannot send the UploadedFile itself, because it may be closed
            # once the thread runs.
            # pylint: disable=consider-using-with
            temp_file = tempfile.NamedTemporaryFile(suffix=extension)
            audio_file.seek(0)
            temp_file.write(audio_file.read())
            temp_file.seek(0)

            logger.info("save_model start thread for %s with audio_file=%s, temp_file=%s", obj, audio_file, temp_file)

            Thread(
                target=self.handle_audio_file_async,
                kwargs={"instance": obj, "temp_file": temp_file},
            ).start()


@admin.register(Post)
class PostAdmin(BasePodcastContentAdmin):
    fields = (
        "podcast",
        "name",
        ("is_draft", "published"),
        "description",
    )
    list_display = (
        "name",
        "is_visible",
        "is_draft",
        "podcast",
        "published",
        "view_count",
        "visitor_count",
        "frontend_link",
    )

    def frontend_link(self, obj: Post):
        return mark_safe(f'<a href="{obj.frontend_url}" target="_blank">' + _("Link") + "</a>")

    def get_list_display(self, request):
        if apps.is_installed("spodcat.logs"):
            return (
                "name",
                "is_visible",
                "is_draft",
                "podcast",
                "published",
                "view_count",
                "visitor_count",
                "frontend_link",
            )
        return ("name", "is_visible", "is_draft", "podcast", "published", "frontend_link")


@admin.register(Artist)
class ArtistAdmin(AdminMixin, admin.ModelAdmin):
    inlines = [ArtistSongInline]
    list_display = ["name", "song_count"]
    list_filter = [ArtistSongCountFilter]
    save_on_top = True
    search_fields = ["name"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(song_count=models.Count("songs"))

    @admin.display(description=_("songs"), ordering="song_count")
    def song_count(self, obj):
        return obj.song_count


@admin.register(EpisodeSong)
class EpisodeSongAdmin(AdminMixin, admin.ModelAdmin):
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

    def get_form(self, request, obj=None, change=False, **kwargs):
        Form = super().get_form(request, obj, change, **kwargs)
        field = Form.base_fields.get("episode")
        if isinstance(field, ModelChoiceField):
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

    @admin.display(description=_("start time"), ordering="start_time")
    def start_time_str(self, obj: EpisodeSong):
        return seconds_to_timestamp(obj.start_time)


@admin.action(description=_("Approve comments"))
def approve_comments(modeladmin, request, queryset):
    queryset.update(is_approved=True)


@admin.register(Comment)
class CommentAdmin(AdminMixin, admin.ModelAdmin):
    actions = [approve_comments]
    list_display = ["name", "truncated_text", "created", "is_approved", "content_link", "frontend_link"]
    list_filter = ["is_approved", "podcast_content__podcast"]
    readonly_fields = ["podcast_content", "name", "text"]

    @admin.display(description=_("content"))
    def content_link(self, obj: Comment):
        return self.get_change_link(obj.podcast_content)

    def frontend_link(self, obj: Comment):
        return mark_safe(f'<a href="{obj.podcast_content.frontend_url}" target="_blank">Link</a>')

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .prefetch_related("podcast_content__podcast__authors")
            .select_related("podcast_content__podcast__owner")
        )

    @admin.display(description=_("text"))
    def truncated_text(self, obj: Comment):
        if len(obj.text) > 1000:
            return obj.text[:1000] + "..."
        return obj.text
