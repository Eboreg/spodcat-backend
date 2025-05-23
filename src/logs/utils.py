import datetime

from azure.identity import DefaultAzureCredential
from azure.monitor.query import (
    LogsQueryClient,
    LogsQueryError,
    LogsQueryStatus,
)
from django.conf import settings
from django.utils import timezone


class GetAudioRequestLogError(Exception):
    def __init__(
        self,
        message,
        podcast_slug: str,
        query_error: LogsQueryError | None = None,
    ):
        super().__init__(message, podcast_slug, query_error)
        self.podcast_slug = podcast_slug
        self.query_error = query_error

        if isinstance(message, list):
            self.error_list = []
            for m in message:
                if not isinstance(m, GetAudioRequestLogError):
                    m = GetAudioRequestLogError(m, podcast_slug)
                self.error_list.extend(m.error_list)
        else:
            self.message = message
            self.error_list = [self]


def get_audio_request_logs(
    podcast_slug: str,
    environment: str | None = None,
    from_date: datetime.datetime | None = None,
    to_date: datetime.datetime | None = None,
    from_inclusive: bool = True,
    to_inclusive: bool = True,
):
    try:
        environment = environment or settings.ENVIRONMENT
        credential = DefaultAzureCredential()
        client = LogsQueryClient(credential)
        from_date = from_date or datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
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
        where_list = [
            "OperationName == 'GetBlob'",
            f"ObjectKey contains '{environment}/{podcast_slug}/episodes'",
            "MetricResponseType == 'Success'",
        ]
        if from_date:
            if timezone.is_naive(from_date):
                from_date = timezone.make_aware(from_date, datetime.timezone.utc)
            if from_inclusive:
                where_list.append(f"TimeGenerated >= todatetime('{from_date.isoformat()}')")
            else:
                where_list.append(f"TimeGenerated > todatetime('{from_date.isoformat()}')")
        if to_date:
            if timezone.is_naive(to_date):
                to_date = timezone.make_aware(to_date, datetime.timezone.utc)
            if to_inclusive:
                where_list.append(f"TimeGenerated <= todatetime('{to_date.isoformat()}')")
            else:
                where_list.append(f"TimeGenerated < todatetime('{to_date.isoformat()}')")
        where = " and ".join(where_list)
        query = f"StorageBlobLogs | where {where} | project {columns}"
        resource_id = (
            f"/subscriptions/{settings.AZURE_SUBSCRIPTION_ID}/resourceGroups/{settings.AZURE_RESOURCE_GROUP}"
            f"/providers/Microsoft.Storage/storageAccounts/{settings.AZURE_ACCOUNT_NAME}"
        )
        response = client.query_resource(resource_id=resource_id, query=query, timespan=(from_date, timezone.now()))

        if response.status != LogsQueryStatus.SUCCESS:
            raise GetAudioRequestLogError(
                "response.status != SUCCESS",
                podcast_slug=podcast_slug,
                query_error=response.partial_error,
            )

        for table in response.tables:
            for row in table.rows:
                # The ">" and "<" operators don't seem to work properly for
                # identical timestamps, so double check here:
                if from_date and not from_inclusive and row["TimeGenerated"] <= from_date:
                    continue
                if to_date and not to_inclusive and row["TimeGenerated"] >= to_date:
                    continue
                yield row

    except Exception as e:
        raise GetAudioRequestLogError(e.args, podcast_slug=podcast_slug) from e


def create_audio_request_logs(
    podcast_slug: str,
    environment: str | None = None,
    no_bots: bool = False,
    complete: bool = False,
):
    from logs.models import PodcastEpisodeAudioRequestLog
    from podcasts.models.episode import Episode

    episodes = list(Episode.objects.filter(podcast__slug=podcast_slug))
    errors: list[GetAudioRequestLogError] = []
    from_date: datetime.datetime | None = None

    if not complete:
        last_log = (
            PodcastEpisodeAudioRequestLog.objects
            .filter(episode__podcast__slug=podcast_slug)
            .order_by("-created")
            .first()
        )
        if last_log:
            from_date = last_log.created

    try:
        for row in get_audio_request_logs(
            podcast_slug=podcast_slug,
            environment=environment,
            from_date=from_date,
            from_inclusive=False,
        ):
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
                errors.append(GetAudioRequestLogError(e.args, podcast_slug=podcast_slug))

    except Exception as e:
        raise GetAudioRequestLogError(e.args, podcast_slug=podcast_slug) from e
