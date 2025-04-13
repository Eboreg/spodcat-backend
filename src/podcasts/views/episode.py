from django.db.models import Prefetch
from django.utils import timezone

from podcasts import serializers
from podcasts.models import Comment, PodcastContent
from podcasts.views.podcast_content import PodcastContentViewSet


class EpisodeViewSet(PodcastContentViewSet):
    filterset_fields = ("slug", "podcast")
    prefetch_for_includes = {
        "podcast.contents": [
            Prefetch(
                "podcast__contents",
                queryset=PodcastContent.objects.partial().visible().prefetch_related("songs"),
            ),
        ],
        "songs": ["songs__artists"],
        "songs.artists": ["songs__artists"],
        "__all__": ["songs", Prefetch("comments", queryset=Comment.objects.filter(is_approved=True))],
    }
    serializer_class = serializers.EpisodeSerializer

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).filter(published__lte=timezone.now(), is_draft=False)
