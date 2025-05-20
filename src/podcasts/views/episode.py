from django.db.models import Prefetch
from django.http.response import JsonResponse
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.request import Request

from podcasts import serializers
from podcasts.models import Comment, PodcastContent
from podcasts.models.episode import Episode
from podcasts.views.podcast_content import (
    PodcastContentFilter,
    PodcastContentViewSet,
)


class EpisodeFilter(PodcastContentFilter):
    episode = filters.CharFilter(method="filter_content")

    class Meta:
        model = Episode
        fields = []


class EpisodeViewSet(PodcastContentViewSet):
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
    def chapters(self, request: Request, pk: str):
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
            "fileName": episode.audio_file.url,
            "chapters": sorted(chapters + songs, key=lambda c: c["startTime"]),
        }

        # pylint: disable=redundant-content-type-for-json-response
        return JsonResponse(
            data=result,
            content_type="application/json+chapters",
            headers={"Content-Disposition": f"attachment; filename=\"{episode.id}.chapters.json\""},
        )
