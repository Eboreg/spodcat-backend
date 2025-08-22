import re

from django.db.models import Prefetch, Q
from django_filters import rest_framework as filters

from spodcat import serializers
from spodcat.models import Comment, Podcast, PodcastContent, Post

from .podcast_content import (
    AbstractPodcastContentViewSet,
    PodcastContentFilter,
)


class PostFilter(PodcastContentFilter):
    post = filters.CharFilter(method="filter_content")

    def filter_freetext(self, queryset, name, value):
        values = re.split(r"\s+", value)
        qs = [
            Q(name__icontains=v) |
            Q(description__icontains=v) |
            Q(videos__title__icontains=v)
            for v in values
        ]
        return queryset.filter(*qs).distinct()


class PostViewSet(AbstractPodcastContentViewSet[Post]):
    filterset_class = PostFilter
    prefetch_for_includes = {
        "podcast.contents": [
            Prefetch(
                "podcast",
                queryset=Podcast.objects.prefetch_related(
                    Prefetch("contents", queryset=PodcastContent.objects.listed().with_has_songs())
                )
            ),
        ],
        "podcast": ["podcast__links", "podcast__categories", "podcast__seasons", "podcast__contents"],
        "__all__": ["videos", Prefetch("comments", queryset=Comment.objects.filter(is_approved=True))],
    }
    serializer_class = serializers.PostSerializer
    queryset = Post.objects.all()

    def get_serializer_class(self):
        if self.is_list_request():
            return serializers.PartialPostSerializer
        return serializers.PostSerializer

    def is_list_request(self):
        return self.action != "retrieve" and "filter[post]" not in self.request.query_params
