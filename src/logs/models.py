import datetime
import ipaddress
import logging
import socket
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from klaatu_django.db import TruncatedCharField
from rest_framework.request import Request

from logs.ip_check import (
    IpAddressCategory,
    get_geoip2_asn,
    get_geoip2_city,
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
from utils.model_mixin import ModelMixin


if TYPE_CHECKING:
    from logs.querysets import PodcastEpisodeAudioRequestLogManager
    from podcasts.models import Episode, Podcast, PodcastContent


logger = logging.getLogger(__name__)


class ReferrerCategory(models.TextChoices):
    APP = "app"
    HOST = "host"


class UserAgent(ModelMixin, models.Model):
    user_agent = models.CharField(max_length=400, primary_key=True)
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

    @classmethod
    def get_or_create(cls, ip: str):
        if ipaddress.ip_address(ip).is_private:
            return None

        try:
            return cls.objects.get(ip=ip)
        except cls.DoesNotExist:
            geoip2_city = get_geoip2_city(ip)
            if geoip2_city:
                geoip2_asn = get_geoip2_asn(ip)
                return cls.objects.create(
                    ip=ip,
                    city=geoip2_city.city.name or "",
                    region=(geoip2_city.subdivisions[0].name or "") if geoip2_city.subdivisions else "",
                    country=geoip2_city.country.iso_code or "",
                    org=(geoip2_asn.autonomous_system_organization or "") if geoip2_asn else "",
                )

        return None


class RequestLog(ModelMixin, models.Model):
    is_bot = models.BooleanField(default=False, db_index=True)
    path_info = TruncatedCharField(max_length=200, blank=True, default="")
    user_agent = models.CharField(max_length=400, blank=True, default="")
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
    remote_host = models.CharField(max_length=100, blank=True, default="")
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
        user_agent_obj = UserAgent.get_or_create(ua_data) if ua_data else None
        geoip = GeoIP.get_or_create(remote_addr) if remote_addr else None
        remote_host = socket.getfqdn(remote_addr) if remote_addr else ""

        obj = cls(
            is_bot=(ua_data and ua_data.is_bot) or remote_addr_category.is_bot,
            referrer=referrer,
            referrer_category=ReferrerCategory(ref_dict["category"]) if ref_dict else None,
            referrer_name=ref_dict["name"] if ref_dict else "",
            remote_addr=remote_addr,
            remote_addr_category=remote_addr_category,
            remote_host=remote_host if remote_host != remote_addr else "",
            user_agent_data=user_agent_obj,
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
            geoip = GeoIP.get_or_create(ip)

            if geoip:
                cls.objects.filter(remote_addr=ip).update(geoip=geoip)

    @classmethod
    def fill_remote_hosts(cls):
        ips = list(
            cls.objects
            .filter(Q(remote_host="") | Q(remote_addr__startswith=F("remote_host")))
            .exclude(remote_addr=None)
            .order_by()
            .values_list("remote_addr", flat=True)
            .distinct()
        )

        for idx, ip in enumerate(ips):
            remote_host = socket.getfqdn(ip)
            if remote_host != ip:
                logger.info("(%d/%d) %s: %s", idx + 1, len(ips), ip, remote_host)
                cls.objects.filter(remote_addr=ip).update(remote_host=remote_host)

    def has_change_permission(self, request):
        return False


class PodcastRequestLog(RequestLog):
    created = models.DateTimeField(db_index=True)
    podcast: "Podcast" = models.ForeignKey("podcasts.Podcast", on_delete=models.CASCADE, related_name="requests")

    class Meta:
        verbose_name = "podcast page request log"
        verbose_name_plural = "podcast page request logs"


class PodcastContentRequestLog(RequestLog):
    created = models.DateTimeField(db_index=True)
    content: "PodcastContent" = models.ForeignKey(
        "podcasts.PodcastContent",
        on_delete=models.CASCADE,
        related_name="requests",
    )

    class Meta:
        verbose_name = "podcast content page request log"
        verbose_name_plural = "podcast content page request logs"


class PodcastEpisodeAudioRequestLog(RequestLog):
    created = models.DateTimeField(db_index=True)
    duration_ms = models.IntegerField()
    episode: "Episode | None" = models.ForeignKey(
        "podcasts.Episode",
        on_delete=models.CASCADE,
        related_name="audio_requests",
    )
    response_body_size = models.IntegerField(db_index=True)
    status_code = models.CharField(max_length=10)

    objects: "PodcastEpisodeAudioRequestLogManager" = PodcastEpisodeAudioRequestLogQuerySet.as_manager()

    @classmethod
    def update_or_create(
        cls,
        user_agent: str | None = None,
        remote_addr: str | None = None,
        referrer: str | None = None,
        created: datetime.datetime | None = None,
        defaults: dict | None = None,
    ):
        defaults = defaults or {}
        obj = cls.create(
            user_agent=user_agent,
            remote_addr=remote_addr,
            referrer=referrer,
            created=created,
            save=False,
            **defaults,
        )
        defaults_keys = [
            "is_bot",
            "referrer",
            "referrer_category",
            "referrer_name",
            "remote_addr_category",
            "remote_host",
            "user_agent_data",
            "user_agent",
            "geoip",
            *defaults,
        ]

        return cls.objects.update_or_create(
            remote_addr=obj.remote_addr,
            created=obj.created,
            defaults={key: getattr(obj, key) for key in defaults_keys},
        )
