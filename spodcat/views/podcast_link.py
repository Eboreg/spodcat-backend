from django_filters import rest_framework as filters
from rest_framework.viewsets import ReadOnlyModelViewSet

from spodcat import serializers
from spodcat.models import PodcastLink
from spodcat.views.mixins import LogRequestMixin


class PodcastLinkFilter(filters.FilterSet):
    podcast = filters.CharFilter(field_name="podcast__slug")


class PodcastLinkViewSet(LogRequestMixin, ReadOnlyModelViewSet[PodcastLink]):
    filterset_class = PodcastLinkFilter
    queryset = PodcastLink.objects.all()
    serializer_class = serializers.PodcastLinkSerializer
