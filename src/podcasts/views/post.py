from django.utils import timezone

from podcasts import serializers
from podcasts.models import Post
from podcasts.views.podcast_content import PodcastContentViewSet


class PostViewSet(PodcastContentViewSet):
    serializer_class = serializers.PostSerializer
    filterset_fields = ("slug", "podcast")

    def get_queryset(self, *args, **kwargs):
        return Post.objects.filter(published__lte=timezone.now(), is_draft=False)
