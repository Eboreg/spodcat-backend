import re
from typing import TypeVar, cast

from django.apps import apps
from django.db.models import Q, QuerySet
from django_filters import rest_framework as filters
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from spodcat import serializers
from spodcat.models import PodcastContent
from spodcat.models.querysets import PodcastContentQuerySet
from spodcat.views.mixins import LogRequestMixin


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


class AbstractPodcastContentViewSet(LogRequestMixin, GenericViewSet[_MT]):
    def filter_queryset(self, queryset):
        queryset = cast(PodcastContentQuerySet, super().filter_queryset(queryset))
        return queryset.published()

    def get_detail_queryset(self, queryset: QuerySet[_MT, _MT]) -> QuerySet[_MT, _MT]:
        return queryset

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        try:
            obj = get_object_or_404(queryset, pk=self.kwargs[lookup_url_kwarg])
        except:
            obj = get_object_or_404(queryset, slug=self.kwargs[lookup_url_kwarg])

        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self) -> QuerySet[_MT, _MT]:
        queryset = super().get_queryset()
        if not self.is_list_request():
            return self.get_detail_queryset(queryset)
        return queryset

    def is_list_request(self):
        return self.action == "list"

    @extend_schema(responses={(200, "text/plain"): OpenApiTypes.NONE})
    @action(methods=["post"], detail=True)
    def pling(self, request: Request, pk: str):
        if apps.is_installed("spodcat.logs"):
            from spodcat.logs.models import PodcastContentRequestLog

            self.log_request(request, PodcastContentRequestLog, content_id=pk)

        return Response()


class PodcastContentViewSet(ListModelMixin, AbstractPodcastContentViewSet[PodcastContent]):
    filterset_class = PodcastContentFilter
    queryset = PodcastContent.objects.with_has_songs()
    serializer_class = serializers.PodcastContentPolymorphicSerializer

    def get_detail_queryset(self, queryset):
        return queryset.select_related("podcast")
