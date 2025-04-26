from django.contrib import admin
from django.forms import ModelChoiceField, ModelForm

from logs.models import (
    GeoIP,
    PodcastContentRequestLog,
    PodcastEpisodeAudioRequestLog,
    PodcastRequestLog,
    UserAgent,
)
from utils.widgets import ReadOnlyInlineModelWidget


class GeoIPWidget(ReadOnlyInlineModelWidget):
    def get_instance_dict(self, instance: GeoIP):
        return {
            "City": instance.city,
            "Region": instance.region,
            "Country": instance.country,
            "Org": instance.org,
        }


class UserAgentWidget(ReadOnlyInlineModelWidget):
    def get_instance_dict(self, instance: UserAgent):
        return {
            "Name": instance.name,
            "Type": instance.get_type_display(),
            "Device category": instance.get_device_category_display(),
            "Device name": instance.device_name,
        }


class LogAdminForm(ModelForm):
    geoip = ModelChoiceField(queryset=GeoIP.objects.all(), widget=GeoIPWidget())
    user_agent_data = ModelChoiceField(queryset=UserAgent.objects.all(), widget=UserAgentWidget())


class LogAdmin(admin.ModelAdmin):
    form = LogAdminForm
    ordering = ["-created"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PodcastRequestLog)
class PodcastRequestLogAdmin(LogAdmin):
    list_display = [
        "created",
        "podcast_link",
        "remote_addr",
        "user_agent_data__name",
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

    @admin.display(description="podcast", ordering="podcast__name")
    def podcast_link(self, obj: PodcastRequestLog):
        return obj.podcast.get_admin_link()


@admin.register(PodcastContentRequestLog)
class PodcastContentRequestLogAdmin(LogAdmin):
    list_display = [
        "created",
        "content_link",
        "podcast_link",
        "remote_addr",
        "user_agent_data__name",
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

    @admin.display(description="content", ordering="content__name")
    def content_link(self, obj: PodcastContentRequestLog):
        return obj.content.get_admin_link()

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("content__podcast", "user_agent_data")

    @admin.display(description="podcast", ordering="content__podcast__name")
    def podcast_link(self, obj: PodcastContentRequestLog):
        return obj.content.podcast.get_admin_link()


@admin.register(PodcastEpisodeAudioRequestLog)
class PodcastEpisodeAudioRequestLogAdmin(LogAdmin):
    list_display = [
        "created",
        "episode_link",
        "podcast_link",
        "remote_addr",
        "user_agent_data__name",
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

    @admin.display(description="episode", ordering="episode__name")
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

    @admin.display(description="% fetched", ordering="percent_fetched")
    def percent_fetched(self, obj):
        return round(obj.percent_fetched, 2)

    @admin.display(description="podcast", ordering="episode__podcast__name")
    def podcast_link(self, obj: PodcastEpisodeAudioRequestLog):
        if obj.episode:
            return obj.episode.podcast.get_admin_link()
        return None
