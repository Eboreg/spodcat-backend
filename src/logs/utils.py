import datetime
import ipaddress
import json
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

from azure.identity import DefaultAzureCredential
from azure.monitor.query import (
    LogsQueryClient,
    LogsQueryError,
    LogsQueryStatus,
)
from django.conf import settings
from django.utils import timezone


if TYPE_CHECKING:
    from logs.models import IpAddressCategory
    from podcasts.models import Podcast


class GetAudioRequestLogError(Exception):
    def __init__(
        self,
        *args,
        podcast: "Podcast",
        query_error: LogsQueryError | None = None,
    ):
        super().__init__(*args)
        self.podcast = podcast
        self.query_error = query_error


def get_audio_request_logs(podcast: "Podcast", environment: str | None = None):
    from logs.models import PodcastContentAudioRequestLog, PodcastRssRequestLog
    from podcasts.models.episode import Episode

    try:
        environment = environment or settings.ENVIRONMENT
        credential = DefaultAzureCredential()
        client = LogsQueryClient(credential)
        last_log = PodcastContentAudioRequestLog.objects.filter(podcast=podcast).order_by("-created").first()
        if last_log:
            from_date = last_log.created
        else:
            from_date = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
        columns = ", ".join([
            "TimeGenerated",
            "StatusCode",
            "DurationMs",
            "CallerIpAddress",
            "UserAgentHeader",
            "ReferrerHeader",
            "ObjectKey",
            "ResponseBodySize",
            "Uri",
        ])
        where = " and ".join([
            "OperationName == 'GetBlob'",
            f"ObjectKey contains '{environment}/{podcast.slug}/episodes'",
            f"TimeGenerated > todatetime('{from_date.isoformat()}')",
        ])
        query = f"StorageBlobLogs | where {where} | project {columns}"
        resource_id = (
            f"/subscriptions/{settings.AZURE_SUBSCRIPTION_ID}/resourceGroups/{settings.AZURE_RESOURCE_GROUP}"
            f"/providers/Microsoft.Storage/storageAccounts/{settings.AZURE_ACCOUNT_NAME}"
        )
        episodes = list(Episode.objects.filter(podcast=podcast))
        response = client.query_resource(resource_id=resource_id, query=query, timespan=(from_date, timezone.now()))
        result: list[PodcastContentAudioRequestLog] = []

        if response.status != LogsQueryStatus.SUCCESS:
            raise GetAudioRequestLogError(podcast=podcast, query_error=response.partial_error)

        for table in response.tables:
            for row in table.rows:
                # The ">" operator doesn't seem to work properly for two
                # identical timestamps, so double check here:
                if row["TimeGenerated"] <= from_date:
                    continue

                try:
                    episode = [
                        ep for ep in episodes
                        if ep.audio_file and row["ObjectKey"].endswith(ep.audio_file.name)
                    ][0]
                except IndexError:
                    episode = None

                qs = parse_qs(urlparse(row["Uri"]).query)
                rss_log_id = qs["_rsslog"][0] if "_rsslog" in qs else None
                rss_request_log = PodcastRssRequestLog.objects.filter(pk=rss_log_id).first() if rss_log_id else None

                result.append(
                    PodcastContentAudioRequestLog.create(
                        user_agent=row["UserAgentHeader"],
                        remote_addr=row["CallerIpAddress"].split(":")[0] if row["CallerIpAddress"] else None,
                        referrer=row["ReferrerHeader"],
                        created=row["TimeGenerated"],
                        duration_ms=row["DurationMs"],
                        episode=episode,
                        path_info=row["ObjectKey"],
                        podcast=podcast,
                        response_body_size=row["ResponseBodySize"] or 0,
                        rss_request_log=rss_request_log,
                        status_code=row["StatusCode"],
                        save=False,
                    )
                )

        if result:
            PodcastContentAudioRequestLog.objects.bulk_create(result)

        return result
    except Exception as e:
        raise GetAudioRequestLogError(*e.args, podcast=podcast) from e


ip_prefix_cache: dict[str, list] = {}


def get_ip_prefix_list(json_filename: str):
    from logs import utils

    cached = utils.ip_prefix_cache.get(json_filename, None)
    if cached is not None:
        return cached

    json_path = Path(settings.BASE_DIR).resolve() / json_filename
    with json_path.open("rt") as f:
        prefixes = json.loads(f.read()).get("prefixes", [])
    utils.ip_prefix_cache[json_filename] = prefixes
    return prefixes


def is_ip_in_prefix_list(ip: str, json_filename: str) -> bool:
    ip_address = ipaddress.ip_address(ip)

    for prefix in get_ip_prefix_list(json_filename):
        if (
            ip_address.version == 4 and
            "ipv4Prefix" in prefix and
            ip_address in ipaddress.ip_network(prefix["ipv4Prefix"])
        ):
            return True
        if (
            ip_address.version == 6 and
            "ipv6Prefix" in prefix and
            ip_address in ipaddress.ip_network(prefix["ipv6Prefix"])
        ):
            return True

    return False


def get_ip_address_category(ip: str | None) -> "IpAddressCategory":
    from logs.models import IpAddressCategory

    if not ip:
        return IpAddressCategory.UNKNOWN
    if is_ip_in_prefix_list(ip, "googlebot.json"):
        return IpAddressCategory.GOOGLEBOT
    if is_ip_in_prefix_list(ip, "special-crawlers.json"):
        return IpAddressCategory.SPECIAL_CRAWLER
    return IpAddressCategory.UNKNOWN
