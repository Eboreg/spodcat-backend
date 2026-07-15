from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet
from django.http import Http404, HttpResponse
from django.template.loader import get_template
from django.template.response import TemplateResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from spodcat import serializers
from spodcat.models import Podcast
from spodcat.rss import PodcastRssData
from spodcat.views.mixins import LogRequestMixin


class PodcastViewSet(LogRequestMixin, ReadOnlyModelViewSet[Podcast]):
    lookup_field = "slug"

    def get_queryset(self) -> QuerySet[Podcast, Podcast]:
        qs = Podcast.objects.select_related("name_font_face")
        if self.action == "list":
            return qs.only("slug", "name", "banner", "cover_thumbnail", "name_font_face", "name_font_size", "tagline")
        return qs.prefetch_related("links")

    def get_serializer_class(self) -> type[serializers.PodcastSerializer]:
        if self.action == "list":
            return serializers.PodcastListSerializer
        return serializers.PodcastSerializer

    @extend_schema(responses={(200, "text/plain"): OpenApiTypes.NONE})
    @action(methods=["post"], detail=True)
    def pling(self, request: Request, pk: str):
        if apps.is_installed("spodcat.logs"):
            from spodcat.logs.models import PodcastRequestLog

            self.log_request(request, PodcastRequestLog, podcast_id=pk)

        return Response()

    @extend_schema(responses={(200, "application/rss+xml"): OpenApiTypes.STR})
    @action(methods=["get"], detail=True)
    def rss(self, request: Request, slug: str):
        # Both template and feedgen methods are available; going with feedgen
        # for now since it's considerably faster in tests.
        try:
            data = PodcastRssData(slug)
        except ObjectDoesNotExist as e:
            raise Http404 from e

        if apps.is_installed("spodcat.logs"):
            from spodcat.logs.models import PodcastRssRequestLog

            self.log_request(request, PodcastRssRequestLog, podcast_id=slug)

        return self.__rss_feedgen(request=request, data=data)

    def __rss_feedgen(self, request: Request, data: PodcastRssData):
        rss = data.fetch_static_or_generate()

        if request.query_params.get("html"):
            return TemplateResponse(
                request=request._request,
                template="spodcat/rss.html",
                context={"rss": rss.decode() if isinstance(rss, bytes) else rss},
            )

        return HttpResponse(
            content=rss,
            content_type="application/rss+xml; charset=utf-8",
            headers={
                "Content-Disposition": f'inline; filename="{data.podcast_slug}.rss.xml"',
                "Access-Control-Allow-Origin": "*",
            },
        )

    def __rss_template(self, request: Request, data: PodcastRssData):
        context = data.get_template_context()

        if request.query_params.get("html"):
            return TemplateResponse(
                request=request._request,
                template="spodcat/rss.html",
                context={"rss": get_template("spodcat/rss.xml").render(context=context)},
            )

        return TemplateResponse(
            request=request._request,
            template="spodcat/rss.xml",
            context=context,
            content_type="application/xml; charset=utf-8",
            headers={
                "Content-Disposition": f'inline; filename="{data.podcast_slug}.rss.xml"',
                "Access-Control-Allow-Origin": "*",
            },
        )
