import re
from io import BytesIO
from time import time

from django.apps import apps
from django.db.models import Q, QuerySet
from django.http import FileResponse, HttpResponseNotFound, HttpResponseRedirect
from django.http.response import JsonResponse
from django_filters import rest_framework as filters
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.request import Request
from rest_framework.viewsets import ReadOnlyModelViewSet

from spodcat import serializers
from spodcat.models import Episode
from spodcat.settings import spodcat_settings
from spodcat.utils import extract_range_request_header, set_range_response_headers
from spodcat.views.podcast_content import AbstractPodcastContentViewSet


class EpisodeFilter(filters.FilterSet):
    freetext = filters.CharFilter(method="filter_freetext", label="Freetext")
    podcast = filters.CharFilter(field_name="podcast__slug")
    slug = filters.CharFilter(field_name="slug")

    def filter_freetext(self, queryset: QuerySet, name, value):
        values = re.split(r"\s+", value)
        qs = [
            Q(name__icontains=v)
            | Q(description__icontains=v)
            | Q(season__name__icontains=v)
            | Q(songs__artists__name__icontains=v)
            | Q(songs__title__icontains=v)
            | Q(songs__comment__icontains=v)
            | Q(videos__title__icontains=v)
            for v in values
        ]
        return queryset.filter(*qs).distinct()


class EpisodeViewSet(ReadOnlyModelViewSet, AbstractPodcastContentViewSet[Episode]):
    filterset_class = EpisodeFilter
    serializer_class = serializers.EpisodeSerializer
    queryset = Episode.objects.with_has_songs()

    def get_detail_queryset(self, queryset):
        return queryset.select_related("podcast", "season").prefetch_related("songs__artists", "videos")

    def get_serializer_class(self):
        if self.is_list_request():
            return serializers.PartialEpisodeSerializer
        return serializers.EpisodeSerializer

    def is_list_request(self):
        return self.action != "retrieve" and not self.request.query_params.get("slug")

    @extend_schema(responses={(200, "audio/*"): OpenApiTypes.BINARY})
    @action(methods=["get"], detail=True)
    def audio(self, request: Request, pk: str):
        queryset = Episode.objects.only("audio_file", "audio_content_type")

        try:
            episode = get_object_or_404(queryset, pk=pk)
        except:
            episode = get_object_or_404(queryset, slug=pk)

        audio_file = episode.audio_file
        range_start = range_end = 0
        duration_ms: int | None = None

        if audio_file.name is None or not audio_file.storage.exists(audio_file.name):
            status_code = 404
            response = HttpResponseNotFound()

        elif not spodcat_settings.USE_INTERNAL_AUDIO_PROXY:
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
                range_end = audio_file.size
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

    @extend_schema(responses={(200, "application/json+chapters"): OpenApiTypes.OBJECT})
    @action(methods=["get"], detail=True)
    def chapters(self, request: Request, pk: str):
        # https://github.com/Podcastindex-org/podcast-namespace/blob/main/docs/examples/chapters/jsonChapters.md
        episode: Episode = (
            self.get_queryset().prefetch_related("songs__artists", "chapters").select_related("podcast").get(id=pk)
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

        return JsonResponse(
            data=result,
            content_type="application/json+chapters",
            headers={"Content-Disposition": f'attachment; filename="{episode.id}.chapters.json"'},
        )
