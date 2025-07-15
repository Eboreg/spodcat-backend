import datetime
import ipaddress
import logging
import socket
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from klaatu_django.db import TruncatedCharField
from rest_framework.request import Request

from spodcat.logs.ip_check import (
    IpAddressCategory,
    get_geoip2_asn,
    get_geoip2_city,
    get_ip_address_category,
)
from spodcat.logs.querysets import (
    PodcastContentRequestLogQuerySet,
    PodcastEpisodeAudioRequestLogQuerySet,
    PodcastRequestLogQuerySet,
    PodcastRssRequestLogQuerySet,
)
from spodcat.logs.user_agent import (
    DeviceCategory,
    UserAgentData,
    UserAgentType,
    get_referrer_dict,
    get_useragent_data,
)
from spodcat.model_mixin import ModelMixin


if TYPE_CHECKING:
    from spodcat.logs.querysets import (
        PodcastContentRequestLogManager,
        PodcastEpisodeAudioRequestLogManager,
        PodcastRequestLogManager,
        PodcastRssRequestLogManager,
    )
    from spodcat.models import Episode, Podcast, PodcastContent


logger = logging.getLogger(__name__)


class ReferrerCategory(models.TextChoices):
    APP = "app"
    HOST = "host"


class UserAgent(ModelMixin, models.Model):
    device_category = models.CharField(
        max_length=20,
        null=True,
        default=None,
        choices=DeviceCategory.choices,
        verbose_name=_("device category"),
    )
    device_name = models.CharField(max_length=40, blank=True, default="", verbose_name=_("device name"))
    name = models.CharField(max_length=100, verbose_name=_("name"))
    type = models.CharField(max_length=10, choices=UserAgentType.choices, db_index=True, verbose_name=_("type"))
    user_agent = models.CharField(max_length=400, primary_key=True, verbose_name=_("user agent"))

    class Meta:
        verbose_name = _("user agent")
        verbose_name_plural = _("user agents")

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
    city = models.CharField(max_length=100, verbose_name=_("city"))
    country = models.CharField(max_length=10, verbose_name=_("country"))
    ip = models.GenericIPAddressField(primary_key=True, verbose_name=_("IP"))
    org = models.CharField(max_length=100, verbose_name=_("org"))
    region = models.CharField(max_length=100, verbose_name=_("region"))

    class Meta:
        verbose_name = _("GeoIP")
        verbose_name_plural = _("GeoIP:s")

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
                return cls.objects.update_or_create(
                    ip=ip,
                    defaults={
                        "city": geoip2_city.city.name or "",
                        "region": (geoip2_city.subdivisions[0].name or "") if geoip2_city.subdivisions else "",
                        "country": geoip2_city.country.iso_code or "",
                        "org": (geoip2_asn.autonomous_system_organization or "") if geoip2_asn else "",
                    },
                )[0]

        return None


class RequestLog(ModelMixin, models.Model):
    created = models.DateTimeField(db_index=True, verbose_name=_("created"))
    geoip = models.ForeignKey["GeoIP | None"](
        "spodcat_logs.GeoIP",
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        related_name="+",
        verbose_name=_("GeoIP"),
    )
    is_bot = models.BooleanField(default=False, db_index=True, verbose_name=_("is bot"))
    path_info = TruncatedCharField(max_length=200, blank=True, default="", verbose_name=_("path"))
    referrer = TruncatedCharField(max_length=150, blank=True, default="", verbose_name=_("referrer"))
    referrer_category = models.CharField(
        max_length=10,
        null=True,
        default=None,
        choices=ReferrerCategory.choices,
        verbose_name=_("referrer category"),
    )
    referrer_name = models.CharField(max_length=50, blank=True, default="", verbose_name=_("referrer name"))
    remote_addr = models.GenericIPAddressField(
        null=True,
        db_index=True,
        default=None,
        verbose_name=_("remote address"),
    )
    remote_addr_category = models.CharField(
        max_length=20,
        choices=IpAddressCategory.choices,
        default=IpAddressCategory.UNKNOWN,
        verbose_name=_("remote address category"),
    )
    remote_host = models.CharField(max_length=100, blank=True, default="", verbose_name=_("remote host"))
    user_agent = models.CharField(max_length=400, blank=True, default="", verbose_name=_("user agent"))
    user_agent_data = models.ForeignKey["UserAgent | None"](
        "spodcat_logs.UserAgent",
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        related_name="+",
        verbose_name=_("user agent data"),
    )

    class Meta:
        verbose_name = _("request log")
        verbose_name_plural = _("request logs")
        abstract = True

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
    podcast = models.ForeignKey["Podcast"](
        "spodcat.Podcast",
        on_delete=models.CASCADE,
        related_name="requests",
        verbose_name=_("podcast"),
    )

    objects: "PodcastRequestLogManager" = PodcastRequestLogQuerySet.as_manager()

    class Meta:
        verbose_name = _("podcast page request log")
        verbose_name_plural = _("podcast page request logs")


class PodcastContentRequestLog(RequestLog):
    content = models.ForeignKey["PodcastContent"](
        "spodcat.PodcastContent",
        on_delete=models.CASCADE,
        related_name="requests",
        verbose_name=_("podcast content"),
    )

    objects: "PodcastContentRequestLogManager" = PodcastContentRequestLogQuerySet.as_manager()

    class Meta:
        verbose_name = _("podcast content page request log")
        verbose_name_plural = _("podcast content page request logs")


class PodcastEpisodeAudioRequestLog(RequestLog):
    duration_ms = models.IntegerField(verbose_name=_("duration"))
    episode = models.ForeignKey["Episode"](
        "spodcat.Episode",
        on_delete=models.CASCADE,
        related_name="audio_requests",
        verbose_name=_("episode"),
    )
    response_body_size = models.IntegerField(db_index=True, verbose_name=_("response body size"))
    status_code = models.CharField(max_length=10, verbose_name=_("status code"))

    objects: "PodcastEpisodeAudioRequestLogManager" = PodcastEpisodeAudioRequestLogQuerySet.as_manager()

    class Meta:
        verbose_name = _("podcast episode audio request log")
        verbose_name_plural = _("podcast episode audio request logs")

    @classmethod
    def update_or_create(
        cls,
        user_agent: str | None = None,
        remote_addr: str | None = None,
        referrer: str | None = None,
        created: datetime.datetime | None = None,
        no_bots: bool = False,
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

        if obj.is_bot and no_bots:
            return None, False

        return cls.objects.update_or_create(
            remote_addr=obj.remote_addr,
            created=obj.created,
            defaults={key: getattr(obj, key) for key in defaults_keys},
        )


class PodcastRssRequestLog(RequestLog):
    podcast = models.ForeignKey["Podcast"](
        "spodcat.Podcast",
        on_delete=models.CASCADE,
        related_name="rss_requests",
        verbose_name=_("podcast"),
    )

    objects: "PodcastRssRequestLogManager" = PodcastRssRequestLogQuerySet.as_manager()
