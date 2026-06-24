import re

from django.db.models import Q, QuerySet
from django_filters import rest_framework as filters
from rest_framework.viewsets import ReadOnlyModelViewSet

from spodcat.models import Episode
from spodcat.v2.serializers.episode import EpisodeSerializer, PartialEpisodeSerializer

from .podcast_content import AbstractPodcastContentViewSet


class EpisodeFilter(filters.FilterSet):
    freetext = filters.CharFilter(method="filter_freetext", label="Freetext")
    podcast = filters.CharFilter(field_name="podcast__slug")
    slug = filters.CharFilter(field_name="slug")

    def filter_freetext(self, queryset: QuerySet, name, value):
        values = re.split(r"\s+", value)
        qs = [
            Q(name__icontains=v)
            | Q(description__icontains=v)
            | Q(season__name__icontains=v)
            | Q(songs__artists__name__icontains=v)
            | Q(songs__title__icontains=v)
            | Q(songs__comment__icontains=v)
            | Q(videos__title__icontains=v)
            for v in values
        ]
        return queryset.filter(*qs).distinct()


class EpisodeViewSet(ReadOnlyModelViewSet, AbstractPodcastContentViewSet[Episode]):
    filterset_class = EpisodeFilter
    serializer_class = EpisodeSerializer

    def get_queryset(self) -> QuerySet:
        qs = Episode.objects.with_has_songs()
        if self.is_list_request():
            return qs
        return qs.select_related("podcast", "season").prefetch_related("songs__artists", "videos")

    def get_serializer_class(self):
        if self.is_list_request():
            return PartialEpisodeSerializer
        return EpisodeSerializer

    def is_list_request(self):
        return self.action != "retrieve" and not self.request.query_params.get("slug")
