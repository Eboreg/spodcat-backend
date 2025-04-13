from typing import TYPE_CHECKING

from django.db import models
from klaatu_django.db import TruncatedCharField
from rest_framework.request import Request

from logs.querysets import PodcastContentAudioRequestLogQuerySet
from podcasts.utils import get_useragent_data


if TYPE_CHECKING:
    from podcasts.models import Episode, Podcast, PodcastContent


class UserAgentType(models.TextChoices):
    APP = "app"
    BOT = "bot"
    BROWSER = "browser"
    LIBRARY = "library"


class DeviceCategory(models.TextChoices):
    AUTO = "auto"
    COMPUTER = "computer"
    MOBILE = "mobile"
    SMART_SPEAKER = "smart_speaker"
    SMART_TV = "smart_tv"
    WATCH = "watch"


class ReferrerCategory(models.TextChoices):
    APP = "app"
    HOST = "host"


class AbstractRequestLog(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    device_category = models.CharField(max_length=20, null=True, default=None, choices=DeviceCategory.choices)
    device_name = models.CharField(max_length=40, null=True, default=None)
    is_bot = models.BooleanField(default=False, db_index=True)
    path_info = TruncatedCharField(max_length=200, blank=True)
    referrer = TruncatedCharField(max_length=100, blank=True)
    referrer_category = models.CharField(max_length=10, null=True, default=None, choices=ReferrerCategory.choices)
    referrer_name = models.CharField(max_length=50, null=True, default=None)
    remote_addr = models.GenericIPAddressField(blank=True, null=True, max_length=50)
    remote_host = TruncatedCharField(max_length=100, blank=True)
    user_agent = TruncatedCharField(max_length=200, blank=True)
    user_agent_name = models.CharField(max_length=100, null=True, default=None)
    user_agent_type = models.CharField(
        max_length=10,
        null=True,
        default=None,
        choices=UserAgentType.choices,
        db_index=True,
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.path_info

    @classmethod
    def create(cls, request: Request, **kwargs):
        data = get_useragent_data(request.headers.get("User-Agent", ""))

        return cls.objects.create(
            device_category=data.device_category if data else None,
            device_name=data.device_name if data else None,
            is_bot=data.is_bot if data else False,
            path_info=request.path_info,
            referrer=request.headers.get("Referer", ""),
            referrer_category=data.referrer_category if data else None,
            referrer_name=data.referrer_name if data else None,
            remote_addr=request.META.get("REMOTE_ADDR", ""),
            remote_host=request.META.get("REMOTE_HOST", ""),
            user_agent_name=data.name if data else None,
            user_agent_type=data.type if data else None,
            user_agent=request.headers.get("User-Agent", ""),
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
    created = models.DateTimeField(db_index=True)
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
    rss_request_log = models.ForeignKey(
        "logs.PodcastRssRequestLog",
        on_delete=models.SET_NULL,
        null=True,
        default=None,
    )
    status_code = models.CharField(max_length=10)

    objects = PodcastContentAudioRequestLogQuerySet.as_manager()
