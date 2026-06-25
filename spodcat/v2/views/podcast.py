from django.apps import apps
from django.db.models.query import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from spodcat.models import Podcast
from spodcat.v2.serializers.podcast import PodcastListSerializer, PodcastSerializer
from spodcat.views.mixins import LogRequestMixin

from .base import V2ViewMixin


class PodcastViewSet(LogRequestMixin, V2ViewMixin, ReadOnlyModelViewSet[Podcast]):
    lookup_field = "slug"

    def get_queryset(self) -> QuerySet[Podcast, Podcast]:
        qs = Podcast.objects.select_related("name_font_face")
        if self.action == "list":
            return qs.only("slug", "name", "banner", "cover_thumbnail", "name_font_face", "name_font_size", "tagline")
        return qs.prefetch_related("links")

    def get_serializer_class(self) -> type[PodcastSerializer]:
        if self.action == "list":
            return PodcastListSerializer
        return PodcastSerializer

    @extend_schema(responses={(200, "text/plain"): OpenApiTypes.NONE})
    @action(methods=["post"], detail=True)
    def ping(self, request: Request, pk: str):
        if apps.is_installed("spodcat.logs"):
            from spodcat.logs.models import PodcastRequestLog

            self.log_request(request, PodcastRequestLog, podcast_id=pk)

        return Response()
