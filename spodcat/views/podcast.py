from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch
from django.http import Http404, HttpResponse
from django.template.loader import get_template
from django.template.response import TemplateResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_json_api import views

from spodcat import serializers
from spodcat.models import Podcast, PodcastContent
from spodcat.rss import PodcastRssData
from spodcat.views.mixins import LogRequestMixin, PreloadIncludesMixin


class PodcastViewSet(LogRequestMixin, PreloadIncludesMixin, views.ReadOnlyModelViewSet[Podcast]):
    prefetch_for_includes = {
        "__all__": [
            "links",
            "categories",
            Prefetch("contents", queryset=PodcastContent.objects.partial().published().with_has_songs()),
        ]
    }
    select_for_includes = {
        "__all__": ["name_font_face"],
    }
    serializer_class = serializers.PodcastSerializer
    queryset = Podcast.objects.order_by_last_content(reverse=True)

    @extend_schema(responses={(200, "text/plain"): OpenApiTypes.NONE})
    @action(methods=["post"], detail=True)
    def ping(self, request: Request, pk: str):
        instance = self.get_object()

        if apps.is_installed("spodcat.logs"):
            from spodcat.logs.models import PodcastRequestLog

            self.log_request(request, PodcastRequestLog, podcast=instance)

        return Response()

    @extend_schema(responses={(200, "application/rss+xml"): OpenApiTypes.STR})
    @action(methods=["get"], detail=True)
    def rss(self, request: Request, pk: str):
        # Both template and feedgen methods are available; going with feedgen
        # for now since it's considerably faster in tests.
        try:
            data = PodcastRssData(pk)
        except ObjectDoesNotExist as e:
            raise Http404 from e

        if apps.is_installed("spodcat.logs"):
            from spodcat.logs.models import PodcastRssRequestLog

            self.log_request(request, PodcastRssRequestLog, podcast=data.podcast)

        return self.__rss_feedgen(request=request, data=data)

    def __rss_feedgen(self, request: Request, data: PodcastRssData):
        rss = data.get_rss_string()

        if request.query_params.get("html"):
            return TemplateResponse(
                request=request._request,  # pylint: disable=protected-access
                template="spodcat/rss.html",
                context={"rss": rss.decode() if isinstance(rss, bytes) else rss},
            )

        return HttpResponse(
            content=rss,
            content_type="application/rss+xml; charset=utf-8",
            headers={
                "Content-Disposition": f'inline; filename="{data.podcast.slug}.rss.xml"',
                "Access-Control-Allow-Origin": "*",
            },
        )

    # pylint: disable=unused-private-member
    def __rss_template(self, request: Request, data: PodcastRssData):
        context = data.get_template_context()

        if request.query_params.get("html"):
            return TemplateResponse(
                request=request._request,  # pylint: disable=protected-access
                template="spodcat/rss.html",
                context={"rss": get_template("spodcat/rss.xml").render(context=context)},
            )

        return TemplateResponse(
            request=request._request,  # pylint: disable=protected-access
            template="spodcat/rss.xml",
            context=context,
            content_type="application/xml; charset=utf-8",
            headers={
                "Content-Disposition": f'inline; filename="{data.podcast.slug}.rss.xml"',
                "Access-Control-Allow-Origin": "*",
            },
        )
