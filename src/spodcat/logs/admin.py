from django.contrib import admin
from django.db.models.functions import Coalesce
from django.forms import ModelChoiceField, ModelForm
from django.utils.translation import gettext_lazy as _

from spodcat.admin.mixins import AdminMixin
from spodcat.logs.models import (
    GeoIP,
    PodcastContentRequestLog,
    PodcastEpisodeAudioRequestLog,
    PodcastRequestLog,
    RequestLog,
    UserAgent,
)
from spodcat.widgets import ReadOnlyInlineModelWidget


class GeoIPWidget(ReadOnlyInlineModelWidget):
    def get_instance_dict(self, instance: GeoIP):
        return {
            _("City"): instance.city,
            _("Region"): instance.region,
            _("Country"): instance.country,
            _("Org"): instance.org,
        }


class UserAgentWidget(ReadOnlyInlineModelWidget):
    def get_instance_dict(self, instance: UserAgent):
        return {
            _("Name"): instance.name,
            _("Type"): instance.get_type_display(),
            _("Device category"): instance.get_device_category_display(),
            _("Device name"): instance.device_name,
        }


class LogAdminForm(ModelForm):
    geoip = ModelChoiceField(queryset=GeoIP.objects.all(), widget=GeoIPWidget())
    user_agent_data = ModelChoiceField(queryset=UserAgent.objects.all(), widget=UserAgentWidget())


class LogAdmin(AdminMixin, admin.ModelAdmin):
    form = LogAdminForm
    ordering = ["-created"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(ordering=Coalesce("user_agent_data__name", "user_agent"))
    def user_agent_name(self, obj: RequestLog):
        if obj.user_agent_data:
            return obj.user_agent_data.name
        return obj.user_agent


@admin.register(PodcastRequestLog)
class PodcastRequestLogAdmin(LogAdmin):
    list_display = [
        "created",
        "podcast_link",
        "remote_addr",
        "user_agent_name",
        "user_agent_data__type",
        "is_bot",
    ]
    list_filter = [
        "created",
        "is_bot",
        ("podcast", admin.RelatedOnlyFieldListFilter),
        "user_agent_data__type",
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("podcast", "user_agent_data")

    @admin.display(description=_("podcast"), ordering="podcast__name")
    def podcast_link(self, obj: PodcastRequestLog):
        return obj.podcast.get_admin_link()


@admin.register(PodcastContentRequestLog)
class PodcastContentRequestLogAdmin(LogAdmin):
    list_display = [
        "created",
        "content_link",
        "podcast_link",
        "remote_addr",
        "user_agent_name",
        "user_agent_data__type",
        "is_bot",
    ]
    list_filter = [
        "created",
        "is_bot",
        ("content__podcast", admin.RelatedOnlyFieldListFilter),
        "user_agent_data__type",
        ("content", admin.RelatedOnlyFieldListFilter),
    ]

    @admin.display(description=_("content"), ordering="content__name")
    def content_link(self, obj: PodcastContentRequestLog):
        return obj.content.get_admin_link()

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("content__podcast", "user_agent_data")

    @admin.display(description=_("podcast"), ordering="content__podcast__name")
    def podcast_link(self, obj: PodcastContentRequestLog):
        return obj.content.podcast.get_admin_link()


@admin.register(PodcastEpisodeAudioRequestLog)
class PodcastEpisodeAudioRequestLogAdmin(LogAdmin):
    list_display = [
        "created",
        "episode_link",
        "podcast_link",
        "remote_addr",
        "user_agent_name",
        "user_agent_data__type",
        "percent_fetched",
        "is_bot",
    ]
    list_filter = [
        "created",
        ("episode__podcast", admin.RelatedOnlyFieldListFilter),
        "is_bot",
        "user_agent_data__type",
        ("episode", admin.RelatedOnlyFieldListFilter),
    ]

    @admin.display(description=_("episode"), ordering="episode__name")
    def episode_link(self, obj: PodcastEpisodeAudioRequestLog):
        if obj.episode:
            return obj.episode.get_admin_link()
        return None

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related("episode__podcast", "user_agent_data")
            .with_percent_fetched()
        )

    @admin.display(description=_("% fetched"), ordering="percent_fetched")
    def percent_fetched(self, obj):
        return round(obj.percent_fetched, 2)

    @admin.display(description=_("podcast"), ordering="episode__podcast__name")
    def podcast_link(self, obj: PodcastEpisodeAudioRequestLog):
        if obj.episode:
            return obj.episode.podcast.get_admin_link()
        return None
