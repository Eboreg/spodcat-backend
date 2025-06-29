from django.db.models import Prefetch
from django_filters import rest_framework as filters

from spodcat import serializers
from spodcat.models import Comment, PodcastContent, Post

from .podcast_content import PodcastContentFilter, PodcastContentViewSet


class PostFilter(PodcastContentFilter):
    post = filters.CharFilter(method="filter_content")


class PostViewSet(PodcastContentViewSet):
    filterset_class = PostFilter
    prefetch_for_includes = {
        "podcast.contents": [
            Prefetch(
                "podcast__contents",
                queryset=PodcastContent.objects.partial().listed().with_has_songs(),
            ),
        ],
        "__all__": [Prefetch("comments", queryset=Comment.objects.filter(is_approved=True))],
    }
    queryset = Post.objects.all()
    serializer_class = serializers.PostSerializer
