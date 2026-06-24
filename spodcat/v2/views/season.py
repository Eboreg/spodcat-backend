from django_filters import rest_framework as filters
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet

from spodcat.models import Season
from spodcat.v2.serializers import SeasonSerializer

from .base import V2ViewMixin


class SeasonFilter(filters.FilterSet):
    podcast = filters.CharFilter(field_name="podcast__slug")


class SeasonViewSet(ListModelMixin, V2ViewMixin, GenericViewSet[Season]):
    filterset_class = SeasonFilter
    queryset = Season.objects.all()
    serializer_class = SeasonSerializer
