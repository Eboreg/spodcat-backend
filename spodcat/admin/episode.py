import logging
import os
import tempfile
from datetime import date, timedelta
from threading import Thread

from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.core.files.uploadedfile import UploadedFile
from django.db.models import Count, F, OuterRef, Subquery, Sum
from django.forms import ModelForm
from django.http import HttpRequest
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from spodcat.admin.podcast_content import BasePodcastContentAdmin, PodcastContentVideoInline
from spodcat.contrib.admin.mixin import AdminMixin
from spodcat.contrib.admin.widgets import ArtistAutocompleteWidget
from spodcat.form_fields import ArtistMultipleChoiceField
from spodcat.forms import EpisodeAdminForm
from spodcat.models import Artist, Episode, EpisodeChapter, EpisodeSong
from spodcat.utils import delete_storage_file


logger = logging.getLogger(__name__)


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


class EpisodeAdmin(BasePodcastContentAdmin[Episode]):
    fields = [
        ("id", "slug"),
        ("name", "podcast"),
        ("season", "number"),
        ("is_draft", "published"),
        "audio_file",
        "image",
        "description",
        "duration",
        "audio_content_type",
        "audio_file_length",
    ]
    inlines = [EpisodeSongInline, EpisodeChapterInline, PodcastContentVideoInline]
    list_filter = ["is_draft", "published", "podcast"]
    readonly_fields = ["audio_content_type", "audio_file_length", "duration", "id", "published"]
    search_fields = ["name", "description", "slug", "songs__title", "songs__artists__name"]
    form = EpisodeAdminForm

    def duration(self, obj: Episode):
        return timedelta(seconds=int(obj.duration_seconds))

    @admin.display(description="")
    def frontend_link(self, obj: Episode):
        return mark_safe(f'<a href="{obj.frontend_url}" target="_blank">' + _("Frontend") + "</a>")

    def get_list_display(self, request: HttpRequest):
        if apps.is_installed("spodcat.logs"):
            return [
                "name",
                "season",
                "number_string",
                "is_visible",
                "podcast_link",
                "published",
                "view_count",
                "play_count",
                "frontend_link",
                "stats_link",
            ]
        return [
            "name",
            "season",
            "number_string",
            "is_visible",
            "podcast_link",
            "published",
            "frontend_link",
        ]

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request).select_related("season")

        if apps.is_installed("spodcat.logs"):
            from spodcat.logs.models import PodcastEpisodeAudioRequestLog

            return qs.annotate(
                play_count=Subquery(
                    PodcastEpisodeAudioRequestLog.objects.filter(is_bot=False).get_play_count_query(
                        episode=OuterRef("pk")
                    )
                ),
            )

        return qs

    def get_urls(self):
        urls = []
        if apps.is_installed("spodcat.logs"):
            urls.append(
                path(
                    "<path:object_id>/stats/",
                    self.admin_site.admin_view(self.stats_view),
                    name=f"{self.opts.app_label}_{self.opts.model_name}_stats",
                )
            )

        return urls + super().get_urls()

    def handle_audio_file_async(self, instance: Episode, filename: str):
        logger.info("handle_audio_file_async starting for %s, filename=%s", instance, filename)

        try:
            instance.get_dbfs_and_duration(filename=filename, delete_file=True)
            logger.info("handle_audio_file_async finished for %s", instance)
        except Exception as e:
            logger.error("handle_audio_file_async error", exc_info=e)

    @admin.display(description=_("number"), ordering="number")
    def number_string(self, obj: Episode):
        return obj.number_string

    @admin.display(description=_("plays"), ordering=F("play_count").asc(nulls_first=True))
    def play_count(self, obj: Episode):
        from spodcat.logs.models import PodcastEpisodeAudioRequestLog

        play_count: float | None = getattr(obj, "play_count")

        if play_count is None:
            return 0.0

        return self.get_changelist_link(
            model=PodcastEpisodeAudioRequestLog,
            text=round(play_count, 2),
            episode__podcastcontent_ptr__exact=obj.pk,
            is_bot__exact=0,
        )

    @admin.display(description=_("podcast"), ordering="podcast")
    def podcast_link(self, obj: Episode):
        return self.get_change_link(obj.podcast)

    def save_form(self, request: HttpRequest, form: ModelForm, change: bool):
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
                if audio_file.content_type:
                    instance.audio_content_type = audio_file.content_type
                instance.audio_file_length = audio_file.size
            else:
                instance.duration_seconds = 0.0
                instance.audio_content_type = ""
                instance.audio_file_length = 0
                instance.dbfs_array = []

        logger.info("save_form finished for %s with audio_file=%s", instance, instance.audio_file)
        return instance

    def save_model(self, request, obj: Episode, form: ModelForm, change: bool):
        super().save_model(request, obj, form, change)

        if "audio_file" in form.changed_data and form.cleaned_data["audio_file"]:
            audio_file: UploadedFile = form.cleaned_data["audio_file"]
            assert audio_file.name
            _, extension = os.path.splitext(os.path.basename(audio_file.name))
            audio_file.seek(0)

            # Cannot send the UploadedFile itself, because it may be closed
            # once the thread runs.
            with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_file:
                temp_file.write(audio_file.read())

            logger.info(
                "save_model start thread for %s with audio_file=%s, filename=%s",
                obj,
                audio_file,
                temp_file.name,
            )

            Thread(
                target=self.handle_audio_file_async,
                kwargs={"instance": obj, "filename": temp_file.name},
            ).start()

    @admin.display(description="")
    def stats_link(self, obj: Episode):
        meta = obj._meta
        url = reverse(f"admin:{meta.app_label}_{meta.model_name}_stats", args=(obj.pk,))
        return mark_safe(f'<a href="{url}">' + _("Statistics") + "</a>")

    def stats_view(self, request: HttpRequest, object_id: str):
        from spodcat.logs.models import (
            PodcastContentRequestLog,
            PodcastEpisodeAudioRequestLog,
        )

        obj = self.get_object(request, unquote(object_id))
        audio_request_log_qs = PodcastEpisodeAudioRequestLog.objects.filter(episode=obj, is_bot=False)
        page_views = PodcastContentRequestLog.objects.filter(content=obj).get_monthly_views()
        plays_qs = audio_request_log_qs.filter(response_body_size__gt=0).with_quota_fetched()
        players_qs = audio_request_log_qs.filter(response_body_size__gt=0)

        return TemplateResponse(
            request=request,
            template="admin/spodcat/episode/stats.html",
            context={
                "opts": self.opts,
                "episode_opts": Episode._meta,
                "object": obj,
                "page_views": page_views,
                "page_views_total": page_views.aggregate(total=Sum("views"))["total"],
                "page_visitors_total": (
                    PodcastContentRequestLog.objects.filter(content=obj).aggregate(
                        visitors=Count("remote_addr", distinct=True)
                    )
                )["visitors"],
                "plays_all_time": plays_qs.aggregate(plays=Sum("quota_fetched"))["plays"],
                "plays_first_week": (
                    plays_qs.filter(created__lte=F("episode__published") + timedelta(days=7)).aggregate(
                        plays=Sum("quota_fetched")
                    )
                )["plays"],
                "players_all_time": players_qs.aggregate(players=Count("remote_addr", distinct=True))["players"],
                "players_first_week": (
                    players_qs.filter(created__lte=F("episode__published") + timedelta(days=7)).aggregate(
                        players=Count("remote_addr", distinct=True)
                    )
                )["players"],
                "top_countries": audio_request_log_qs.get_ip_count_query(ccode=F("geoip__country")),
                "top_apps": audio_request_log_qs.get_ip_count_query(app_name=F("user_agent_data__name")),
                "top_devices": audio_request_log_qs.get_ip_count_query(device_name=F("user_agent_data__device_name")),
                "title": _("Statistics"),
                "subtitle": str(obj),
                "media": self.media,
                "graph_start_date": date.today() - relativedelta(months=1),
                **self.admin_site.each_context(request),
            },
        )
