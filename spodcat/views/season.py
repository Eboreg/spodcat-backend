from django_filters import rest_framework as filters
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet

from spodcat import serializers
from spodcat.models import Season


class SeasonFilter(filters.FilterSet):
    podcast = filters.CharFilter(field_name="podcast__slug")


class SeasonViewSet(ListModelMixin, GenericViewSet[Season]):
    filterset_class = SeasonFilter
    queryset = Season.objects.only("id", "name", "number", "image", "image_thumbnail")
    serializer_class = serializers.SeasonSerializer
