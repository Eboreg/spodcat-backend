from django.db.models import Prefetch

from podcasts import serializers
from podcasts.models import Comment, PodcastContent
from podcasts.models.episode import Episode
from podcasts.views.podcast_content import PodcastContentViewSet


class EpisodeViewSet(PodcastContentViewSet):
    filterset_fields = ("slug", "podcast")
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
