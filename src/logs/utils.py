import datetime
from typing import TYPE_CHECKING

from azure.identity import DefaultAzureCredential
from azure.monitor.query import (
    LogsQueryClient,
    LogsQueryError,
    LogsQueryStatus,
)
from django.conf import settings
from django.utils import timezone


if TYPE_CHECKING:
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
    from logs.models import PodcastEpisodeAudioRequestLog
    from podcasts.models.episode import Episode

    try:
        environment = environment or settings.ENVIRONMENT
        credential = DefaultAzureCredential()
        client = LogsQueryClient(credential)
        last_log = PodcastEpisodeAudioRequestLog.objects.filter(episode__podcast=podcast).order_by("-created").first()
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
        result: list[PodcastEpisodeAudioRequestLog] = []

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
                    continue

                result.append(
                    PodcastEpisodeAudioRequestLog.create(
                        user_agent=row["UserAgentHeader"],
                        remote_addr=row["CallerIpAddress"].split(":")[0] if row["CallerIpAddress"] else None,
                        referrer=row["ReferrerHeader"],
                        created=row["TimeGenerated"],
                        duration_ms=row["DurationMs"],
                        episode=episode,
                        path_info=row["ObjectKey"],
                        response_body_size=row["ResponseBodySize"] or 0,
                        status_code=row["StatusCode"],
                    )
                )

        return result
    except Exception as e:
        raise GetAudioRequestLogError(*e.args, podcast=podcast) from e
