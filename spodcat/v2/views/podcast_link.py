from django_filters import rest_framework as filters
from rest_framework.viewsets import ReadOnlyModelViewSet

from spodcat.models.podcast_link import PodcastLink
from spodcat.v2.serializers.podcast_link import PodcastLinkSerializer
from spodcat.views.mixins import LogRequestMixin

from .base import V2ViewMixin


class PodcastLinkFilter(filters.FilterSet):
    podcast = filters.CharFilter(field_name="podcast__slug")


class PodcastLinkViewSet(LogRequestMixin, V2ViewMixin, ReadOnlyModelViewSet[PodcastLink]):
    filterset_class = PodcastLinkFilter
    queryset = PodcastLink.objects.all()
    serializer_class = PodcastLinkSerializer
