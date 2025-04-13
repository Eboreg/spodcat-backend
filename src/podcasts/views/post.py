from django.db.models import Prefetch
from django.utils import timezone

from podcasts import serializers
from podcasts.models import Comment, PodcastContent, Post
from podcasts.views.podcast_content import PodcastContentViewSet


class PostViewSet(PodcastContentViewSet):
    filterset_fields = ("slug", "podcast")
    prefetch_for_includes = {
        "podcast.contents": [
            Prefetch(
                "podcast__contents",
                queryset=PodcastContent.objects.partial().visible().prefetch_related("songs"),
            ),
        ],
        "__all__": [Prefetch("comments", queryset=Comment.objects.filter(is_approved=True))],
    }
    serializer_class = serializers.PostSerializer

    def get_queryset(self, *args, **kwargs):
        return Post.objects.filter(published__lte=timezone.now(), is_draft=False)
