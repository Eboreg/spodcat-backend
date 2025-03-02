from django.contrib import admin

from logs.models import (
    EpisodeAudioRequestLog,
    PodcastContentRequestLog,
    PodcastRequestLog,
    PodcastRssRequestLog,
)


@admin.register(PodcastRequestLog, PodcastRssRequestLog, PodcastContentRequestLog, EpisodeAudioRequestLog)
class LogAdmin(admin.ModelAdmin):
    list_display = ("path_info", "created", "remote_addr", "remote_host")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
