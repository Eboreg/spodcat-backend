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
        message,
        podcast: "Podcast",
        query_error: LogsQueryError | None = None,
    ):
        super().__init__(message, podcast, query_error)
        self.podcast = podcast
        self.query_error = query_error

        if isinstance(message, list):
            self.error_list = []
            for m in message:
                if not isinstance(m, GetAudioRequestLogError):
                    m = GetAudioRequestLogError(m, podcast)
                self.error_list.extend(m.error_list)
        else:
            self.message = message
            self.error_list = [self]


def get_audio_request_logs(
    podcast: "Podcast",
    environment: str | None = None,
    complete: bool = False,
    no_bots: bool = False,
):
    from logs.models import PodcastEpisodeAudioRequestLog
    from podcasts.models.episode import Episode

    try:
        environment = environment or settings.ENVIRONMENT
        credential = DefaultAzureCredential()
        client = LogsQueryClient(credential)
        from_date = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
        if not complete:
            last_log = (
                PodcastEpisodeAudioRequestLog.objects
                .filter(episode__podcast=podcast)
                .order_by("-created")
                .first()
            )
            if last_log:
                from_date = last_log.created
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
        errors: list[GetAudioRequestLogError] = []

        if response.status != LogsQueryStatus.SUCCESS:
            raise GetAudioRequestLogError(
                "response.status != SUCCESS",
                podcast=podcast,
                query_error=response.partial_error,
            )

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

                try:
                    log, created = PodcastEpisodeAudioRequestLog.update_or_create(
                        user_agent=row["UserAgentHeader"],
                        remote_addr=row["CallerIpAddress"].split(":")[0] if row["CallerIpAddress"] else None,
                        referrer=row["ReferrerHeader"],
                        created=row["TimeGenerated"],
                        no_bots=no_bots,
                        defaults={
                            "duration_ms": row["DurationMs"],
                            "episode": episode,
                            "path_info": row["ObjectKey"],
                            "response_body_size": row["ResponseBodySize"] or 0,
                            "status_code": row["StatusCode"],
                        },
                    )
                    if created and log:
                        yield log
                except Exception as e:
                    errors.append(GetAudioRequestLogError(e.args, podcast=podcast))
        if errors:
            raise GetAudioRequestLogError(errors, podcast=podcast)
    except Exception as e:
        raise GetAudioRequestLogError(e.args, podcast=podcast) from e
