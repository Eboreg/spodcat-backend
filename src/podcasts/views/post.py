from django.db.models import Prefetch

from podcasts import serializers
from podcasts.models import Comment, PodcastContent, Post
from podcasts.views.podcast_content import PodcastContentViewSet


class PostViewSet(PodcastContentViewSet):
    filterset_fields = ("slug", "podcast")
    prefetch_for_includes = {
        "podcast.contents": [
            Prefetch(
                "podcast__contents",
                queryset=PodcastContent.objects.partial().visible().with_has_songs(),
            ),
        ],
        "__all__": [Prefetch("comments", queryset=Comment.objects.filter(is_approved=True))],
    }
    queryset = Post.objects.all()
    serializer_class = serializers.PostSerializer
