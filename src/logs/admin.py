from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from logs.models import (
    AbstractPodcastRequestLog,
    PodcastContentAudioRequestLog,
    PodcastContentRequestLog,
    PodcastRequestLog,
    PodcastRssRequestLog,
    UserAgentType,
)
from podcasts.models.episode import Episode
from podcasts.models.post import Post


class LogAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class UserAgentTypeFilter(admin.SimpleListFilter):
    parameter_name = "user_agent_type"
    title = "user agent type"

    def lookups(self, request, model_admin):
        return [
            ("except_bot", "All except Bot"),
            *UserAgentType.choices,
        ]

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        if self.value() == "except_bot":
            return queryset.exclude(user_agent_type=UserAgentType.BOT)
        return queryset.filter(user_agent_type=self.value())


@admin.register(PodcastRequestLog, PodcastRssRequestLog)
class PodcastRequestLogAdmin(LogAdmin):
    list_display = ["created", "podcast_link", "remote_addr", "user_agent_name", "user_agent_type"]
    list_filter = ["created", "podcast", UserAgentTypeFilter]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("podcast")

    @admin.display(description="podcast", ordering="podcast__name")
    def podcast_link(self, obj: AbstractPodcastRequestLog):
        return format_html(
            '<a class="nowrap" href="{url}">{name}</a>',
            url=reverse("admin:podcasts_podcast_change", args=(obj.podcast.pk,)),
            name=str(obj.podcast),
        )


@admin.register(PodcastContentRequestLog)
class PodcastContentRequestLogAdmin(LogAdmin):
    list_display = ["created", "content_link", "podcast_link", "remote_addr", "user_agent_name", "user_agent_type"]
    list_filter = ["created", "content__podcast", UserAgentTypeFilter]

    @admin.display(description="content", ordering="content__name")
    def content_link(self, obj: PodcastContentRequestLog):
        content_class = obj.content.get_real_instance_class()
        if content_class is Episode:
            view = "admin:podcasts_episode_change"
        elif content_class is Post:
            view = "admin:podcasts_post_change"
        else:
            return ""

        return format_html(
            '<a href="{url}">{name}</a>',
            url=reverse(view, args=(obj.content.pk,)),
            name=str(obj.content),
        )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("content__podcast")

    @admin.display(description="podcast", ordering="content__podcast__name")
    def podcast_link(self, obj: PodcastContentRequestLog):
        return format_html(
            '<a class="nowrap" href="{url}">{name}</a>',
            url=reverse("admin:podcasts_podcast_change", args=(obj.content.podcast.pk,)),
            name=str(obj.content.podcast),
        )


@admin.register(PodcastContentAudioRequestLog)
class PodcastContentAudioRequestLogAdmin(LogAdmin):
    list_display = [
        "created",
        "episode_link",
        "podcast_link",
        "remote_addr",
        "percent_fetched",
        "seconds_fetched",
        "user_agent_name",
        "user_agent_type",
    ]
    list_filter = ["created", "podcast", UserAgentTypeFilter]

    @admin.display(description="episode", ordering="episode__name")
    def episode_link(self, obj: PodcastContentAudioRequestLog):
        if obj.episode:
            return format_html(
                '<a href="{url}">{name}</a>',
                url=reverse("admin:podcasts_episode_change", args=(obj.episode.pk,)),
                name=str(obj.episode),
            )
        return None

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related("podcast", "episode")
            .with_percent_fetched()
            .with_seconds_fetched()
        )

    @admin.display(description="% fetched")
    def percent_fetched(self, obj):
        return obj.percent_fetched

    @admin.display(description="podcast", ordering="podcast__name")
    def podcast_link(self, obj: PodcastContentAudioRequestLog):
        return format_html(
            '<a class="nowrap" href="{url}">{name}</a>',
            url=reverse("admin:podcasts_podcast_change", args=(obj.podcast.pk,)),
            name=str(obj.podcast),
        )

    @admin.display(description="seconds fetched")
    def seconds_fetched(self, obj):
        return obj.seconds_fetched
