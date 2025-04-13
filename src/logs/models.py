from typing import TYPE_CHECKING

from django.db import models
from klaatu_django.db import TruncatedCharField
from rest_framework.request import Request

from logs.querysets import PodcastContentAudioRequestLogQuerySet
from podcasts.utils import get_useragent_dict


if TYPE_CHECKING:
    from podcasts.models import Episode, Podcast, PodcastContent


class AbstractRequestLog(models.Model):
    class UserAgentType(models.TextChoices):
        BOT = "bot"
        APP = "app"
        LIBRARY = "library"
        BROWSER = "browser"

    created = models.DateTimeField(auto_now_add=True)
    path_info = TruncatedCharField(max_length=200, blank=True)
    referer = TruncatedCharField(max_length=100, blank=True)
    remote_addr = models.GenericIPAddressField(blank=True, null=True, max_length=50)
    remote_host = TruncatedCharField(max_length=100, blank=True)
    user_agent = TruncatedCharField(max_length=200, blank=True)
    user_agent_type = models.CharField(max_length=10, null=True, default=None, choices=UserAgentType.choices)

    class Meta:
        abstract = True

    def __str__(self):
        return self.path_info

    @classmethod
    def create(cls, request: Request, **kwargs):
        ua_type, _ = get_useragent_dict(request.headers.get("User-Agent", ""))

        return cls.objects.create(
            remote_host=request.META.get("REMOTE_HOST", ""),
            remote_addr=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.headers.get("User-Agent", ""),
            referer=request.headers.get("Referer", ""),
            path_info=request.path_info,
            user_agent_type=ua_type,
            **kwargs,
        )


class AbstractPodcastRequestLog(AbstractRequestLog):
    podcast: "Podcast"

    class Meta:
        abstract = True


class PodcastRequestLog(AbstractPodcastRequestLog):
    podcast: "Podcast" = models.ForeignKey("podcasts.Podcast", on_delete=models.CASCADE, related_name="requests")

    class Meta:
        verbose_name = "podcast page request log"
        verbose_name_plural = "podcast page request logs"


class PodcastRssRequestLog(AbstractPodcastRequestLog):
    podcast: "Podcast" = models.ForeignKey("podcasts.Podcast", on_delete=models.CASCADE, related_name="rss_requests")

    class Meta:
        verbose_name = "podcast RSS request log"
        verbose_name_plural = "podcast RSS request logs"


class PodcastContentRequestLog(AbstractRequestLog):
    content: "PodcastContent" = models.ForeignKey(
        "podcasts.PodcastContent",
        on_delete=models.CASCADE,
        related_name="requests",
    )

    class Meta:
        verbose_name = "podcast content page request log"
        verbose_name_plural = "podcast content page request logs"


class PodcastContentAudioRequestLog(AbstractPodcastRequestLog):
    created = models.DateTimeField()
    duration_ms = models.IntegerField()
    episode: "Episode | None" = models.ForeignKey(
        "podcasts.Episode",
        on_delete=models.SET_NULL,
        related_name="audio_requests",
        null=True,
        default=None,
    )
    podcast: "Podcast" = models.ForeignKey("podcasts.Podcast", on_delete=models.CASCADE, related_name="audio_requests")
    response_body_size = models.IntegerField()
    status_code = models.CharField(max_length=10)
    rss_user_agent_type = models.CharField(max_length=10, null=True, default=None)

    objects = PodcastContentAudioRequestLogQuerySet.as_manager()
