from django.db.models import Prefetch
from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.request import Request

from logs.models import EpisodeAudioRequestLog
from podcasts import serializers
from podcasts.models import Comment, Episode, PodcastContent
from podcasts.views.podcast_content import PodcastContentViewSet


class EpisodeViewSet(PodcastContentViewSet):
    serializer_class = serializers.EpisodeSerializer
    prefetch_for_includes = {
        "songs.artists": ["songs__artists"],
        "songs": ["songs__artists"],
        "podcast.contents": [
            Prefetch(
                "podcast__contents",
                queryset=PodcastContent.objects.partial().visible().prefetch_related("songs"),
            ),
        ],
        "__all__": ["songs", Prefetch("comments", queryset=Comment.objects.filter(is_approved=True))],
    }
    filterset_fields = ("slug", "podcast")

    @action(methods=["get"], detail=True)
    def audio(self, request: Request, pk: str):
        episode: Episode = self.get_queryset().get(slug=pk)
        EpisodeAudioRequestLog.create(request=request, content=episode)
        return HttpResponseRedirect(episode.audio_file.url)

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).filter(published__lte=timezone.now(), is_draft=False)
