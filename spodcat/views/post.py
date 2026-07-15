import re

from django.db.models import Q, QuerySet
from django_filters import rest_framework as filters
from rest_framework.viewsets import ReadOnlyModelViewSet

from spodcat import serializers
from spodcat.models import Post
from spodcat.views.podcast_content import AbstractPodcastContentViewSet


class PostFilter(filters.FilterSet):
    freetext = filters.CharFilter(method="filter_freetext", label="Freetext")
    podcast = filters.CharFilter(field_name="podcast__slug")
    slug = filters.CharFilter(field_name="slug")

    def filter_freetext(self, queryset: QuerySet, name, value):
        values = re.split(r"\s+", value)
        qs = [Q(name__icontains=v) | Q(description__icontains=v) | Q(videos__title__icontains=v) for v in values]
        return queryset.filter(*qs).distinct()


class PostViewSet(ReadOnlyModelViewSet, AbstractPodcastContentViewSet[Post]):
    filterset_class = PostFilter
    queryset = Post.objects.all()
    serializer_class = serializers.PostSerializer

    def get_detail_queryset(self, queryset):
        return queryset.select_related("podcast")

    def get_serializer_class(self):
        if self.is_list_request():
            return serializers.PartialPostSerializer
        return serializers.PostSerializer

    def is_list_request(self):
        return self.action != "retrieve" and not self.request.query_params.get("slug")
