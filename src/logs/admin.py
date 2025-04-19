from django.contrib import admin

from logs.models import (
    AbstractPodcastRequestLog,
    PodcastContentAudioRequestLog,
    PodcastContentRequestLog,
    PodcastRequestLog,
    PodcastRssRequestLog,
)


class LogAdmin(admin.ModelAdmin):
    ordering = ["-created"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PodcastRequestLog, PodcastRssRequestLog)
class PodcastRequestLogAdmin(LogAdmin):
    list_display = ["created", "podcast_link", "remote_addr", "user_agent_name", "user_agent_type", "is_bot"]
    list_filter = [
        "created",
        "is_bot",
        ("podcast", admin.RelatedOnlyFieldListFilter),
        "user_agent_type",
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("podcast")

    @admin.display(description="podcast", ordering="podcast__name")
    def podcast_link(self, obj: AbstractPodcastRequestLog):
        return obj.podcast.get_admin_link()


@admin.register(PodcastContentRequestLog)
class PodcastContentRequestLogAdmin(LogAdmin):
    list_display = [
        "created",
        "content_link",
        "podcast_link",
        "remote_addr",
        "user_agent_name",
        "user_agent_type",
        "is_bot",
    ]
    list_filter = [
        "created",
        "is_bot",
        ("content__podcast", admin.RelatedOnlyFieldListFilter),
        "user_agent_type",
        ("content", admin.RelatedOnlyFieldListFilter),
    ]

    @admin.display(description="content", ordering="content__name")
    def content_link(self, obj: PodcastContentRequestLog):
        return obj.content.get_admin_link()

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("content__podcast")

    @admin.display(description="podcast", ordering="content__podcast__name")
    def podcast_link(self, obj: PodcastContentRequestLog):
        return obj.content.podcast.get_admin_link()


@admin.register(PodcastContentAudioRequestLog)
class PodcastContentAudioRequestLogAdmin(LogAdmin):
    list_display = [
        "created",
        "episode_link",
        "podcast_link",
        "remote_addr",
        "user_agent_name",
        "user_agent_type",
        "percent_fetched",
        "is_bot",
    ]
    list_filter = [
        "created",
        ("episode__podcast", admin.RelatedOnlyFieldListFilter),
        "is_bot",
        "user_agent_type",
        ("episode", admin.RelatedOnlyFieldListFilter),
    ]

    @admin.display(description="episode", ordering="episode__name")
    def episode_link(self, obj: PodcastContentAudioRequestLog):
        if obj.episode:
            return obj.episode.get_admin_link()
        return None

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("episode__podcast").with_percent_fetched()

    @admin.display(description="% fetched", ordering="percent_fetched")
    def percent_fetched(self, obj):
        return obj.percent_fetched

    @admin.display(description="podcast", ordering="episode__podcast__name")
    def podcast_link(self, obj: PodcastContentAudioRequestLog):
        if obj.episode:
            return obj.episode.podcast.get_admin_link()
        return None
