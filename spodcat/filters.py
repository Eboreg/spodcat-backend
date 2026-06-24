from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django_filters import rest_framework as filters
from rest_framework_json_api.django_filters import (
    DjangoFilterBackend as BaseDjangoFilterBackend,
)


class IdListFilter(filters.FilterSet):
    id = filters.CharFilter(method="filter_id")

    def filter_id(self, queryset: QuerySet, name, value):
        ids = value.split(",")
        try:
            return queryset.filter(id__in=ids)
        except ValidationError:
            return queryset.none()


class DjangoFilterBackend(BaseDjangoFilterBackend):
    search_param = "filter[search]"
