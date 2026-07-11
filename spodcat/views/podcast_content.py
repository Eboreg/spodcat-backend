from typing import cast
from uuid import UUID

from django.apps import apps
from django.db.models import Q, QuerySet
from django_filters import rest_framework as filters
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_json_api import views

from spodcat.filters import IdListFilter
from spodcat.models.querysets import PodcastContentQuerySet
from spodcat.views.mixins import LogRequestMixin, PreloadIncludesMixin


class AbstractPodcastContentFilter(IdListFilter):
    freetext = filters.CharFilter(method="filter_freetext", label="Free text")
    podcast = filters.CharFilter(field_name="podcast__slug")

    def filter_content(self, queryset: QuerySet, name, value):
        try:
            uuid = UUID(hex=value)
            return queryset.filter(Q(slug=value) | Q(pk=uuid))
        except ValueError:
            return queryset.filter(slug=value)


class AbstractPodcastContentViewSet(LogRequestMixin, PreloadIncludesMixin, views.ReadOnlyModelViewSet):
    select_for_includes = {
        "season": ["season__podcast"],
        "__all__": ["podcast"],
    }

    def filter_queryset(self, queryset):
        queryset = cast(PodcastContentQuerySet, super().filter_queryset(queryset))
        return queryset.published()

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        try:
            obj = get_object_or_404(queryset, pk=self.kwargs[lookup_url_kwarg])
        except:
            obj = get_object_or_404(queryset, slug=self.kwargs[lookup_url_kwarg])

        self.check_object_permissions(self.request, obj)
        return obj

    @extend_schema(responses={(200, "text/plain"): OpenApiTypes.NONE})
    @action(methods=["post"], detail=True)
    def ping(self, request: Request, pk: str):
        if apps.is_installed("spodcat.logs"):
            from spodcat.logs.models import PodcastContentRequestLog

            self.log_request(request, PodcastContentRequestLog, content_id=pk)

        return Response()
