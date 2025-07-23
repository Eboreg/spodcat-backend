from datetime import date, timedelta

from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from spodcat import serializers
from spodcat.logs.graph_data import PeriodicalGraphData
from spodcat.time_period import Day, Month, TimePeriod, Week, Year


class GraphView(APIView):
    renderer_classes=[JSONRenderer, BrowsableAPIRenderer]
    authentication_classes=[SessionAuthentication]
    permission_classes=[IsAuthenticated]

    def get(self, request: Request, *args, **kwargs):
        from spodcat.logs.models import (
            PodcastEpisodeAudioRequestLog,
            PodcastRssRequestLog,
        )

        graph_type = request.query_params["type"]
        graph_data: PeriodicalGraphData | None = None
        podcast_id = request.query_params.get("podcast")
        episode_id = request.query_params.get("episode")
        grouped = podcast_id is None and episode_id is None
        start_date = (
            date.fromisoformat(request.query_params["start"])
            if "start" in request.query_params
            else date.today() - timedelta(days=30)
        )
        end_date = (
            date.fromisoformat(request.query_params["end"])
            if "end" in request.query_params
            else date.today()
        )
        period = self.get_graph_period_type(request)

        graph_qs = PodcastEpisodeAudioRequestLog.objects.filter(is_bot=False).filter_by_user(request.user)
        if episode_id:
            graph_qs = graph_qs.filter(episode=episode_id)
        elif podcast_id:
            graph_qs = graph_qs.filter(episode__podcast=podcast_id)

        if graph_type == "episode-plays":
            graph_data = graph_qs.get_episode_play_count_graph_data(
                period=period or Day,
                start_date=start_date,
                end_date=end_date,
            )
        elif graph_type == "podcast-plays":
            graph_data = graph_qs.get_podcast_play_count_graph_data(
                period=period or Day,
                grouped=grouped,
                start_date=start_date,
                end_date=end_date,
            )
        elif graph_type == "unique-ips":
            graph_data = graph_qs.get_unique_ips_graph_data(
                period=period or Month,
                grouped=grouped,
                average=False,
                start_date=start_date,
                end_date=end_date,
            )
        elif graph_type == "rss-unique-ips":
            graph_qs = (
                PodcastRssRequestLog.objects.filter(is_bot=False).exclude(user_agent="").filter_by_user(request.user)
            )
            if episode_id:
                graph_qs = graph_qs.filter(podcast__contents=episode_id)
            elif podcast_id:
                graph_qs = graph_qs.filter(podcast=podcast_id)
            graph_data = graph_qs.get_unique_ips_graph_data(
                period=period or Month,
                grouped=grouped,
                average=True,
                start_date=start_date,
                end_date=end_date,
            )

        if graph_data:
            serializer = serializers.GraphSerializer({
                "datasets": graph_data.get_datasets(start_date, end_date),
                "earliestDate": graph_data.earliest_date,
            })
            return Response(serializer.data)

        raise ValidationError({"type": "Not a valid graph type."})

    def get_graph_period_type(self, request: Request) -> type[TimePeriod] | None:
        match request.query_params.get("period"):
            case "day":
                return Day
            case "week":
                return Week
            case "month":
                return Month
            case "year":
                return Year
        return None
