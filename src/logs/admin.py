from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from logs.models import (
    AbstractPodcastContentRequestLog,
    AbstractPodcastRequestLog,
    EpisodeAudioRequestLog,
    PodcastContentRequestLog,
    PodcastRequestLog,
    PodcastRssRequestLog,
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


@admin.register(PodcastRequestLog, PodcastRssRequestLog)
class PodcastRequestLogAdmin(LogAdmin):
    list_display = ["created", "podcast_link", "remote_addr", "remote_host"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("podcast")

    @admin.display(description="podcast", ordering="podcast__name")
    def podcast_link(self, obj: AbstractPodcastRequestLog):
        return format_html(
            "<a href=\"{url}\">{name}</a>",
            url=reverse("admin:podcasts_podcast_change", args=(obj.podcast.pk,)),
            name=str(obj.podcast),
        )


@admin.register(PodcastContentRequestLog, EpisodeAudioRequestLog)
class PodcastContentRequestLogAdmin(LogAdmin):
    list_display = ["created", "content_link", "remote_addr", "remote_host"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("content__podcast")

    @admin.display(description="content", ordering="content__name")
    def content_link(self, obj: AbstractPodcastContentRequestLog):
        content_class = obj.content.get_real_instance_class()
        if content_class is Episode:
            view = "admin:podcasts_episode_change"
        elif content_class is Post:
            view = "admin:podcasts_post_change"
        else:
            return ""

        return format_html(
            "<a href=\"{url}\">{name}</a>",
            url=reverse(view, args=(obj.content.pk,)),
            name=str(obj.content),
        )

    @admin.display(description="podcast", ordering="content__podcast__name")
    def podcast_link(self, obj: AbstractPodcastContentRequestLog):
        return format_html(
            "<a href=\"{url}\">{name}</a>",
            url=reverse("admin:podcasts_podcast_change", args=(obj.content.podcast.pk,)),
            name=str(obj.content.podcast),
        )
