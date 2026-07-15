import statistics
from datetime import timedelta
from typing import TYPE_CHECKING

from django.apps import apps
from django.contrib import admin
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.admin.utils import unquote
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Avg, Count, F, FloatField, Max, Min, Sum
from django.db.models.functions import Cast
from django.forms import ModelForm
from django.http import HttpRequest, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from spodcat.contrib.admin.mixin import AdminMixin, StaticRSSMixin
from spodcat.forms import PodcastAdminForm, PodcastChangeSlugForm
from spodcat.models import Episode, Podcast, PodcastLink
from spodcat.utils import delete_storage_file


if TYPE_CHECKING:
    from django.contrib.admin.options import _FieldsetSpec


class PodcastLinkInline(AdminMixin, admin.TabularInline):
    model = PodcastLink
    extra = 0


class PodcastAdmin(AdminMixin, StaticRSSMixin[Podcast], admin.ModelAdmin):
    filter_horizontal = ["categories", "authors"]
    inlines = [PodcastLinkInline]
    readonly_fields = ("slug",)
    save_on_top = True
    form = PodcastAdminForm

    @admin.display(description=_("authors"))
    def author_links(self, obj: Podcast):
        return mark_safe("<br>".join(self.get_change_link(u) for u in obj.authors.all()))

    def change_slug_view(self, request: HttpRequest, object_id: str):
        obj = self.get_object(request, unquote(object_id))

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            return self._get_obj_does_not_exist_redirect(request, self.opts, object_id)  # type: ignore

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
            template="admin/spodcat/podcast/change_slug.html",
            context={"opts": self.opts, "form": form, **self.admin_site.each_context(request)},
        )

    @admin.display(description="")
    def frontend_link(self, obj: Podcast):
        return mark_safe(f'<a href="{obj.frontend_url}" target="_blank">' + _("Frontend") + "</a>")

    def get_fieldsets(self, request: HttpRequest, obj: Podcast | None = None) -> "_FieldsetSpec":
        fieldsets: "_FieldsetSpec" = [
            (None, {"fields": [("name", "slug"), ("tagline", "language"), "description", "episode_rss_suffix"]}),
            (
                _("Comments"),
                {
                    "fields": [
                        ("enable_comments", "require_comment_approval"),
                    ]
                },
            ),
            (_("Graphics"), {"fields": ["cover", "banner", "favicon", "name_font_size", "name_font_face"]}),
        ]

        if obj:
            fieldsets.append((None, {"fields": ["categories", "owner", "authors", "custom_guid", "itunes_type"]}))
        else:
            fieldsets.append((None, {"fields": ["categories", "custom_guid", "itunes_type"]}))

        return fieldsets

    def get_list_display(self, request: HttpRequest):
        if apps.is_installed("spodcat.logs"):
            return [
                "name",
                "slug",
                "owner_link",
                "author_links",
                "view_count",
                "play_count",
                "frontend_link",
                "stats_link",
            ]
        return ["name", "slug", "owner_link", "author_links", "frontend_link"]

    def get_podcast_slugs_from_instance(self, obj: Podcast) -> list[str]:
        return [obj.slug]

    def get_podcast_slugs_from_queryset(self, queryset: models.QuerySet[Podcast, Podcast]) -> list[str]:
        return list(queryset.values_list("slug", flat=True))

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request).prefetch_related("authors").select_related("owner", "name_font_face")

        if apps.is_installed("spodcat.logs"):
            return qs.annotate(view_count=Count("requests", distinct=True))

        return qs

    def get_urls(self):
        urls = [
            path(
                "<path:object_id>/change_slug/",
                self.admin_site.admin_view(self.change_slug_view),
                name=f"{self.opts.app_label}_{self.opts.model_name}_change_slug",
            ),
        ]
        if apps.is_installed("spodcat.logs"):
            urls.append(
                path(
                    "<path:object_id>/stats/",
                    self.admin_site.admin_view(self.stats_view),
                    name=f"{self.opts.app_label}_{self.opts.model_name}_stats",
                )
            )

        return urls + super().get_urls()

    @admin.display(description=_("owner"))
    def owner_link(self, obj: Podcast):
        return self.get_change_link(obj.owner)

    @admin.display(description=_("plays"))
    def play_count(self, obj: Podcast):
        from spodcat.logs.models import PodcastEpisodeAudioRequestLog

        play_count = (
            PodcastEpisodeAudioRequestLog.objects.filter(is_bot=False, episode__podcast=obj).aggregate(
                play_count=Sum(Cast(F("response_body_size"), FloatField()) / F("episode__audio_file_length"))
            )
        )["play_count"]

        if play_count is None:
            return 0.0

        return self.get_changelist_link(
            model=PodcastEpisodeAudioRequestLog,
            text=round(play_count, 2),
            episode__podcast__slug__exact=obj.pk,
            is_bot__exact=0,
        )

    def save_form(self, request: HttpRequest, form: ModelForm, change: bool):
        instance: Podcast = super().save_form(request, form, change)

        if not change:
            assert isinstance(request.user, AbstractUser)
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

    @admin.display(description="")
    def stats_link(self, obj: Podcast):
        meta = obj._meta
        url = reverse(f"admin:{meta.app_label}_{meta.model_name}_stats", args=(obj.pk,))
        return mark_safe(f'<a href="{url}">' + _("Statistics") + "</a>")

    def stats_view(self, request: HttpRequest, object_id: str):
        from spodcat.logs.models import (
            PodcastContentRequestLog,
            PodcastEpisodeAudioRequestLog,
            PodcastRequestLog,
        )

        obj = self.get_object(request, unquote(object_id))
        audio_request_log_qs = PodcastEpisodeAudioRequestLog.objects.filter(episode__podcast=obj, is_bot=False)
        home_page_views = PodcastRequestLog.objects.filter(podcast=obj).get_monthly_views()
        content_page_views = PodcastContentRequestLog.objects.filter(content__podcast=obj).get_monthly_views()
        episode_qs = Episode.objects.filter(podcast=obj).published()
        episode_dates = episode_qs.aggregate(first=Min("published"), last=Max("published"))
        episode_count = episode_qs.count()
        episode_durations = episode_qs.aggregate(
            total=Sum("duration_seconds"),
            max=Max("duration_seconds"),
            min=Min("duration_seconds"),
            avg=Avg("duration_seconds"),
        )
        episode_durations["median"] = statistics.median(episode_qs.values_list("duration_seconds", flat=True))
        top_episodes_all_time = audio_request_log_qs.get_most_played().filter(plays__gte=0.05)

        if episode_dates["first"] and episode_dates["last"] and episode_count > 1:
            episode_interval = (episode_dates["last"] - episode_dates["first"]) / (episode_count - 1)
        else:
            episode_interval = None

        return TemplateResponse(
            request=request,
            template="admin/spodcat/podcast/stats.html",
            context={
                "opts": self.opts,
                "episode_opts": Episode._meta,
                "object": obj,
                "home_page_views": home_page_views,
                "home_page_views_total": home_page_views.aggregate(total=Sum("views"))["total"],
                "home_page_visitors_total": (
                    PodcastRequestLog.objects.filter(podcast=obj).aggregate(
                        visitors=Count("remote_addr", distinct=True)
                    )
                )["visitors"],
                "content_page_views": content_page_views,
                "content_page_views_total": content_page_views.aggregate(total=Sum("views"))["total"],
                "content_page_visitors_total": (
                    PodcastContentRequestLog.objects.filter(content__podcast=obj).aggregate(
                        visitors=Count("remote_addr", distinct=True)
                    )
                )["visitors"],
                "published_episodes": Episode.objects.filter(podcast=obj).published().count(),
                "episode_durations": episode_durations,
                "episode_interval": episode_interval,
                "top_episodes_all_time": top_episodes_all_time,
                "top_episode_first_week": top_episodes_all_time.filter(
                    created__lte=F("episode__published") + timedelta(days=7)
                ),
                "top_countries": audio_request_log_qs.get_ip_count_query(ccode=F("geoip__country")),
                "top_apps": audio_request_log_qs.get_ip_count_query(app_name=F("user_agent_data__name")),
                "top_devices": audio_request_log_qs.get_ip_count_query(device_name=F("user_agent_data__device_name")),
                "title": _("Statistics"),
                "subtitle": str(obj),
                "media": self.media,
                **self.admin_site.each_context(request),
            },
        )

    @admin.display(description=_("views"), ordering="view_count")
    def view_count(self, obj: Podcast):
        from spodcat.logs.models import PodcastRequestLog

        view_count: int = getattr(obj, "view_count", 0)

        if not view_count:
            return 0

        return self.get_changelist_link(
            model=PodcastRequestLog,
            text=view_count,
            podcast__slug__exact=obj.pk,
        )
