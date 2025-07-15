from io import BytesIO
from time import time

from django.apps import apps
from django.db.models import Prefetch
from django.db.models.fields.files import FieldFile
from django.http import FileResponse, HttpResponseRedirect
from django.http.response import JsonResponse
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.request import Request

from spodcat import serializers
from spodcat.models import Comment, Episode, PodcastContent
from spodcat.settings import spodcat_settings
from spodcat.utils import (
    extract_range_request_header,
    set_range_response_headers,
)

from .podcast_content import PodcastContentFilter, PodcastContentViewSet


class EpisodeFilter(PodcastContentFilter):
    episode = filters.CharFilter(method="filter_content")


class EpisodeViewSet(PodcastContentViewSet[Episode]):
    filterset_class = EpisodeFilter
    prefetch_for_includes = {
        "podcast.contents": [
            Prefetch(
                "podcast__contents",
                queryset=PodcastContent.objects.partial().listed().with_has_songs(),
            ),
        ],
        "songs": ["songs__artists"],
        "songs.artists": ["songs__artists"],
        "__all__": ["songs", Prefetch("comments", queryset=Comment.objects.filter(is_approved=True))],
    }
    queryset = Episode.objects.with_has_songs()
    serializer_class = serializers.EpisodeSerializer

    @action(methods=["get"], detail=True)
    def audio(self, request: Request, pk: str):
        episode = self.get_object()
        audio_file: FieldFile = episode.audio_file
        range_start = 0
        range_end = audio_file.size
        duration_ms: int | None = None

        if not spodcat_settings.USE_INTERNAL_AUDIO_PROXY:
            status_code = 302
            response = HttpResponseRedirect(audio_file.url)
        else:
            status_code = 200
            range_header = extract_range_request_header(request)
            start_time = int(time() * 1000)

            if range_header:
                range_start, range_end = range_header

                with audio_file.open() as f:
                    f.seek(range_start)
                    buf = BytesIO(f.read(range_end - range_start))

                status_code = 206
                response = FileResponse(buf, content_type=episode.audio_content_type, status=status_code)
                set_range_response_headers(response, range_start, range_end, audio_file.size)
            else:
                response = FileResponse(audio_file.open(), content_type=episode.audio_content_type)

            response["Accept-Ranges"] = "bytes"
            duration_ms = int(time() * 1000) - start_time

        if apps.is_installed("spodcat.logs"):
            from spodcat.logs.models import PodcastEpisodeAudioRequestLog
            self.log_request(
                request,
                PodcastEpisodeAudioRequestLog,
                episode=episode,
                response_body_size=range_end - range_start,
                status_code=status_code,
                duration_ms=duration_ms,
            )

        return response

    @action(methods=["get"], detail=True)
    def chapters(self, request: Request, pk: str):
        # https://github.com/Podcastindex-org/podcast-namespace/blob/main/docs/examples/chapters/jsonChapters.md
        episode: Episode = (
            self.get_queryset()
            .prefetch_related("songs__artists", "chapters")
            .select_related("podcast")
            .get(id=pk)
        )
        songs = [song.to_dict() for song in episode.songs.all()]
        chapters = [chapter.to_dict() for chapter in episode.chapters.all()]
        result = {
            "version": "1.2.0",
            "title": episode.name,
            "podcastName": episode.podcast.name,
            "fileName": episode.get_audio_file_url(),
            "chapters": sorted(chapters + songs, key=lambda c: c["startTime"]),
        }

        # pylint: disable=redundant-content-type-for-json-response
        return JsonResponse(
            data=result,
            content_type="application/json+chapters",
            headers={"Content-Disposition": f"attachment; filename=\"{episode.id}.chapters.json\""},
        )
