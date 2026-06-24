from django.apps import apps
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from spodcat.models import Podcast
from spodcat.v2.serializers.podcast import PodcastSerializer
from spodcat.views.mixins import LogRequestMixin

from .base import V2ViewMixin


class PodcastViewSet(LogRequestMixin, V2ViewMixin, ReadOnlyModelViewSet[Podcast]):
    lookup_field = "slug"
    serializer_class = PodcastSerializer
    queryset = (
        Podcast.objects.order_by_last_content(reverse=True)
        .select_related("name_font_face")
        .prefetch_related("links")
    )

    @extend_schema(responses={(200, "text/plain"): OpenApiTypes.NONE})
    @action(methods=["post"], detail=True)
    def ping(self, request: Request, pk: str):
        instance = self.get_object()

        if apps.is_installed("spodcat.logs"):
            from spodcat.logs.models import PodcastRequestLog

            self.log_request(request, PodcastRequestLog, podcast=instance)

        return Response()
