from django.db.models import Prefetch
from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.request import Request

from podcasts import serializers
from podcasts.models import Comment, Episode, PodcastContent
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

    @action(methods=["get"], detail=True)
    def audio(self, request: Request, pk: str):
        episode: Episode = self.get_object()
        return HttpResponseRedirect(episode.audio_file.url)

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).filter(published__lte=timezone.now(), is_draft=False)
