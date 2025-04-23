import ipaddress
from pathlib import Path
from typing import NotRequired, TypedDict

import geocoder
from django.conf import settings
from django.db import models
from geocoder.base import MultipleResultsQuery


class IpAddressCategory(models.TextChoices):
    APPLEBOT = "applebot"
    BINGBOT = "bingbot"
    DUCKDUCKBOT = "duckduckbot"
    FACEBOOKBOT = "facebookbot"
    GOOGLEBOT = "googlebot"
    TWITTERBOT = "twitterbot"
    UNKNOWN = "unknown"

    @property
    def is_bot(self):
        return self != IpAddressCategory.UNKNOWN


class GeoProperties(TypedDict):
    address: str
    city: str
    country: str
    hostname: NotRequired[str]
    ip: str
    lat: float
    lng: float
    ok: bool
    org: str
    postal: str
    state: str
    status: str


ip_list_cache: dict[IpAddressCategory, list[ipaddress.IPv4Network | ipaddress.IPv6Network]] = {}


def get_geo_properties(ip: str) -> GeoProperties | None:
    try:
        results: MultipleResultsQuery = geocoder.ip(ip)
    except Exception as e:
        raise ValueError(f"Exception getting geoip for {ip}", e) from e

    if not results.ok or (isinstance(results.status_code, int) and results.status_code >= 400):
        raise ValueError(f"Error getting geoip for {ip}", results)

    features = results.geojson.get("features", [])

    if isinstance(features, list) and features:
        feature = features[0]
        if isinstance(feature, dict) and "properties" in feature:
            properties: GeoProperties = feature["properties"]
            if properties["ok"]:
                return properties

    return None


def get_ip_address_category(ip: str | None) -> IpAddressCategory:
    if not ip:
        return IpAddressCategory.UNKNOWN

    for category in IpAddressCategory:
        if category != IpAddressCategory.UNKNOWN and is_ip_in_category(ip, category):
            return category

    return IpAddressCategory.UNKNOWN


def get_ip_network_list(category: IpAddressCategory) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    from logs import ip_check

    if category == IpAddressCategory.UNKNOWN:
        return []

    cached = ip_check.ip_list_cache.get(category, None)
    if cached is not None:
        return cached

    path = Path(settings.BASE_DIR).resolve() / f"GoodBots/iplists/{category.value}.ips"
    with path.open("rt") as f:
        networks = [ipaddress.ip_network(line.strip()) for line in f]

    ip_check.ip_list_cache[category] = networks
    return networks


def is_ip_in_category(ip: str, category: IpAddressCategory) -> bool:
    ip_address = ipaddress.ip_address(ip)

    for network in get_ip_network_list(category):
        if ip_address.version == network.version and ip_address in network:
            return True

    return False
