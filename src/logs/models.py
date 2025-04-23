import datetime
import ipaddress
import logging
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone
from klaatu_django.db import TruncatedCharField
from rest_framework.request import Request

from logs.ip_check import (
    IpAddressCategory,
    get_geo_properties,
    get_ip_address_category,
)
from logs.querysets import PodcastEpisodeAudioRequestLogQuerySet
from logs.user_agent import (
    DeviceCategory,
    UserAgentData,
    UserAgentType,
    get_referrer_dict,
    get_useragent_data,
)
from model_mixin import ModelMixin


if TYPE_CHECKING:
    from podcasts.models import Episode, Podcast, PodcastContent


logger = logging.getLogger(__name__)


class ReferrerCategory(models.TextChoices):
    APP = "app"
    HOST = "host"


class UserAgent(ModelMixin, models.Model):
    user_agent = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=UserAgentType.choices, db_index=True)
    device_category = models.CharField(max_length=20, null=True, default=None, choices=DeviceCategory.choices)
    device_name = models.CharField(max_length=40, blank=True, default="")

    @classmethod
    def get_or_create(cls, data: UserAgentData, save: bool = True):
        try:
            return cls.objects.get(user_agent=data.user_agent)
        except cls.DoesNotExist:
            obj = cls(
                user_agent=data.user_agent,
                name=data.name,
                type=data.type,
                device_category=data.device_category,
                device_name=data.device_name,
            )
            if save:
                obj.save()
            return obj


class GeoIP(ModelMixin, models.Model):
    ip = models.GenericIPAddressField(primary_key=True)
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    country = models.CharField(max_length=10)
    org = models.CharField(max_length=100)
    hostname = models.CharField(max_length=100)

    @classmethod
    def get_or_create(cls, ip: str):
        if ipaddress.ip_address(ip).is_private:
            return None

        try:
            return cls.objects.get(ip=ip)
        except cls.DoesNotExist:
            try:
                properties = get_geo_properties(ip)
            except Exception as e:
                logger.error("Exception getting geoip for %s", ip, exc_info=e)
                return None
            if properties:
                return cls.objects.create(
                    ip=ip,
                    city=properties["city"],
                    region=properties["state"],
                    country=properties["country"],
                    org=properties["org"],
                    hostname=properties.get("hostname", ""),
                )

        return None


class RequestLog(ModelMixin, models.Model):
    created = models.DateTimeField(db_index=True)
    is_bot = models.BooleanField(default=False, db_index=True)
    path_info = TruncatedCharField(max_length=200, blank=True, default="")
    user_agent = models.CharField(max_length=255, blank=True, default="")
    user_agent_data = models.ForeignKey(
        "logs.UserAgent",
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        related_name="logs",
    )
    remote_addr = models.GenericIPAddressField(null=True, db_index=True, default=None)
    remote_addr_category = models.CharField(
        max_length=20,
        choices=IpAddressCategory.choices,
        default=IpAddressCategory.UNKNOWN,
    )
    geoip = models.ForeignKey(
        "logs.GeoIP",
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        related_name="logs",
    )
    referrer = TruncatedCharField(max_length=100, blank=True, default="")
    referrer_category = models.CharField(max_length=10, null=True, default=None, choices=ReferrerCategory.choices)
    referrer_name = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        ordering = ["-created"]

    @classmethod
    def create(
        cls,
        user_agent: str | None = None,
        remote_addr: str | None = None,
        referrer: str | None = None,
        save: bool = True,
        created: datetime.datetime | None = None,
        **kwargs,
    ):
        user_agent = user_agent or ""
        remote_addr = remote_addr or None
        referrer = referrer or ""
        created = created or timezone.now()

        ua_data = get_useragent_data(user_agent)
        ref_dict = get_referrer_dict(referrer) if ua_data and ua_data.type == "browser" else None

        remote_addr_category = get_ip_address_category(remote_addr)
        user_agent_data = UserAgent.get_or_create(ua_data) if ua_data else None
        geoip = GeoIP.get_or_create(remote_addr) if remote_addr else None

        obj = cls(
            is_bot=(ua_data and ua_data.is_bot) or remote_addr_category.is_bot,
            referrer=referrer,
            referrer_category=ReferrerCategory(ref_dict["category"]) if ref_dict else None,
            referrer_name=ref_dict["name"] if ref_dict else "",
            remote_addr=remote_addr,
            remote_addr_category=remote_addr_category,
            user_agent_data=user_agent_data,
            user_agent=user_agent,
            geoip=geoip,
            created=created,
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

    @classmethod
    def fill_geoips(cls):
        ips = list(
            cls.objects
            .filter(geoip=None)
            .exclude(remote_addr=None)
            .order_by()
            .values_list("remote_addr", flat=True)
            .distinct()
        )

        for idx, ip in enumerate(ips):
            logger.info("(%d/%d) %s", idx + 1, len(ips), ip)
            geo_properties = get_geo_properties(ip)

            if geo_properties:
                geoip = GeoIP.objects.create(
                    ip=ip,
                    city=geo_properties["city"],
                    region=geo_properties["state"],
                    country=geo_properties["country"],
                    org=geo_properties["org"],
                    hostname=geo_properties.get("hostname", ""),
                )
                cls.objects.filter(remote_addr=ip).update(geoip=geoip)

    def has_change_permission(self, request):
        return False


class AbstractPodcastRequestLog(RequestLog):
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


class PodcastContentRequestLog(RequestLog):
    content: "PodcastContent" = models.ForeignKey(
        "podcasts.PodcastContent",
        on_delete=models.CASCADE,
        related_name="requests",
    )

    class Meta:
        verbose_name = "podcast content page request log"
        verbose_name_plural = "podcast content page request logs"


class PodcastEpisodeAudioRequestLog(RequestLog):
    duration_ms = models.IntegerField()
    episode: "Episode | None" = models.ForeignKey(
        "podcasts.Episode",
        on_delete=models.CASCADE,
        related_name="audio_requests",
    )
    response_body_size = models.IntegerField(db_index=True)
    rss_request_log = models.ForeignKey(
        "logs.PodcastRssRequestLog",
        on_delete=models.SET_NULL,
        null=True,
        default=None,
    )
    status_code = models.CharField(max_length=10)

    objects = PodcastEpisodeAudioRequestLogQuerySet.as_manager()
