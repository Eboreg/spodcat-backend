from django.http import HttpResponseRedirect
from rest_framework.decorators import action
from rest_framework.request import Request

from logs.models import EpisodeAudioRequestLog
from podcasts import serializers
from podcasts.models import Episode
from podcasts.views.podcast_content import PodcastContentViewSet


class EpisodeViewSet(PodcastContentViewSet):
    serializer_class = serializers.EpisodeSerializer
    prefetch_for_includes = {
        "songs": ["songs__artists"],
        "__all__": ["songs"],
    }
    queryset = Episode.objects.all()

    @action(methods=["get"], detail=True)
    def audio(self, request: Request, pk: str):
        episode: Episode = self.get_queryset().get(slug=pk)
        EpisodeAudioRequestLog.create(request=request, content=episode)
        return HttpResponseRedirect(episode.audio_file.url)
