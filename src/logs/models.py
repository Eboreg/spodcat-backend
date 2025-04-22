from typing import TYPE_CHECKING

from django.db import models
from klaatu_django.db import TruncatedCharField
from logs.ip_check import IpAddressCategory, get_ip_address_category
from rest_framework.request import Request

from logs.querysets import PodcastContentAudioRequestLogQuerySet
from model_mixin import ModelMixin
from podcasts.user_agent import get_useragent_data


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


class AbstractRequestLog(ModelMixin, models.Model):
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    device_category = models.CharField(max_length=20, null=True, default=None, choices=DeviceCategory.choices)
    device_name = models.CharField(max_length=40, blank=True, default="")
    is_bot = models.BooleanField(default=False, db_index=True)
    path_info = TruncatedCharField(max_length=200, blank=True)
    referrer = TruncatedCharField(max_length=100, blank=True)
    referrer_category = models.CharField(max_length=10, null=True, default=None, choices=ReferrerCategory.choices)
    referrer_name = models.CharField(max_length=50, blank=True, default="")
    remote_addr = models.GenericIPAddressField(blank=True, null=True, max_length=50, db_index=True)
    remote_addr_category = models.CharField(
        max_length=20,
        choices=IpAddressCategory.choices,
        default=IpAddressCategory.UNKNOWN,
    )
    user_agent = TruncatedCharField(max_length=200, blank=True)
    user_agent_name = models.CharField(max_length=100, blank=True, default="")
    user_agent_type = models.CharField(
        max_length=10,
        null=True,
        default=None,
        choices=UserAgentType.choices,
        db_index=True,
    )

    class Meta:
        abstract = True
        ordering = ["-created"]

    def __str__(self):
        return self.path_info

    @classmethod
    def create(
        cls,
        user_agent: str | None = None,
        remote_addr: str | None = None,
        referrer: str | None = None,
        save: bool = True,
        **kwargs,
    ):
        user_agent = user_agent or ""
        remote_addr = remote_addr or None
        referrer = referrer or ""
        ua_data = get_useragent_data(user_agent, referrer)
        remote_addr_category = get_ip_address_category(remote_addr)

        obj = cls(
            device_category=ua_data.device_category if ua_data else None,
            device_name=ua_data.device_name if ua_data else "",
            is_bot=(ua_data and ua_data.is_bot) or remote_addr_category.is_bot,
            referrer=referrer,
            referrer_category=ua_data.referrer_category if ua_data else None,
            referrer_name=ua_data.referrer_name if ua_data else "",
            remote_addr=remote_addr,
            remote_addr_category=remote_addr_category,
            user_agent_name=ua_data.name if ua_data else "",
            user_agent_type=ua_data.type if ua_data else None,
            user_agent=user_agent,
            **kwargs,
        )

        if save:
            obj.save()
        return obj

    @classmethod
    def create_from_request(cls, request: Request, **kwargs):
        return cls.create(
            user_agent=request.headers.get("User-Agent", ""),
            remote_addr=request.META.get("REMOTE_ADDR", None),
            referrer=request.headers.get("Referer", ""),
            path_info=request.path_info,
            **kwargs,
        )

    def has_change_permission(self, request):
        return False


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
    response_body_size = models.IntegerField(db_index=True)
    rss_request_log = models.ForeignKey(
        "logs.PodcastRssRequestLog",
        on_delete=models.SET_NULL,
        null=True,
        default=None,
    )
    status_code = models.CharField(max_length=10)

    objects = PodcastContentAudioRequestLogQuerySet.as_manager()
