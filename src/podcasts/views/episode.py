from django.db.models import Prefetch
from django_filters import rest_framework as filters

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
                queryset=PodcastContent.objects.partial().visible().with_has_songs(),
            ),
        ],
        "songs": ["songs__artists"],
        "songs.artists": ["songs__artists"],
        "__all__": ["songs", Prefetch("comments", queryset=Comment.objects.filter(is_approved=True))],
    }
    queryset = Episode.objects.with_has_songs()
    serializer_class = serializers.EpisodeSerializer
