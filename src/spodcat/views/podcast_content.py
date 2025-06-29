from uuid import UUID

from django.db.models import Q
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_json_api import views

from spodcat import serializers
from spodcat.filters import IdListFilter
from spodcat.models import PodcastContent, PodcastContentRequestLog


class PodcastContentFilter(IdListFilter):
    podcast = filters.CharFilter(method="filter_podcast")

    def filter_content(self, queryset, name, value):
        try:
            uuid = UUID(hex=value)
            return queryset.filter(Q(slug=value) | Q(pk=uuid))
        except ValueError:
            return queryset.filter(slug=value)

    def filter_podcast(self, queryset, name, value):
        return queryset.filter(podcast__slug=value)


class PodcastContentViewSet(views.ReadOnlyModelViewSet):
    queryset = PodcastContent.objects.all()
    select_for_includes = {
        "podcast": ["podcast"],
    }
    serializer_class = serializers.PodcastContentSerializer

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action == "list":
            return queryset.listed()
        return queryset.published()

    @action(methods=["post"], detail=True)
    def ping(self, request: Request, pk: str):
        instance = self.get_object()
        PodcastContentRequestLog.create_from_request(request=request, content=instance)
        return Response()
