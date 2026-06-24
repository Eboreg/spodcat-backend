import re
from typing import TypeVar, cast

from django.apps import apps
from django.db.models import Q, QuerySet
from django_filters import rest_framework as filters
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from spodcat.models import PodcastContent
from spodcat.models.querysets import PodcastContentQuerySet
from spodcat.v2.serializers.podcast_content import PodcastContentPolymorphicSerializer
from spodcat.views.mixins import LogRequestMixin

from .base import V2ViewMixin


_MT = TypeVar("_MT", bound=PodcastContent)


class PodcastContentFilter(filters.FilterSet):
    freetext = filters.CharFilter(method="filter_freetext", label="Freetext")
    podcast = filters.CharFilter(field_name="podcast__slug")

    def filter_freetext(self, queryset: QuerySet, name, value):
        values = re.split(r"\s+", value)
        qs = [
            Q(name__icontains=v)
            | Q(description__icontains=v)
            | Q(episode__season__name__icontains=v)
            | Q(episode__songs__artists__name__icontains=v)
            | Q(episode__songs__title__icontains=v)
            | Q(episode__songs__comment__icontains=v)
            | Q(videos__title__icontains=v)
            for v in values
        ]
        return queryset.filter(*qs).distinct()


class AbstractPodcastContentViewSet(LogRequestMixin, V2ViewMixin, GenericViewSet[_MT]):
    def filter_queryset(self, queryset):
        queryset = cast(PodcastContentQuerySet, super().filter_queryset(queryset))
        return queryset.published()

    def is_list_request(self):
        return self.action == "list"

    @extend_schema(responses={(200, "text/plain"): OpenApiTypes.NONE})
    @action(methods=["post"], detail=True)
    def ping(self, request: Request, pk: str):
        instance = self.get_object()

        if apps.is_installed("spodcat.logs"):
            from spodcat.logs.models import PodcastContentRequestLog

            self.log_request(request, PodcastContentRequestLog, content=instance)

        return Response()


class PodcastContentViewSet(ListModelMixin, AbstractPodcastContentViewSet[PodcastContent]):
    filterset_class = PodcastContentFilter
    serializer_class = PodcastContentPolymorphicSerializer

    def get_queryset(self):
        qs = PodcastContent.objects.with_has_songs()
        if self.is_list_request():
            return qs
        return qs.select_related("podcast")
