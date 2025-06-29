from django_filters import rest_framework as filters
from rest_framework_json_api.django_filters import (
    DjangoFilterBackend as BaseDjangoFilterBackend,
)


class IdListFilter(filters.FilterSet):
    id = filters.CharFilter(method="filter_id")

    def filter_id(self, queryset, name, value):
        ids = value.split(",")
        return queryset.filter(id__in=ids)


class DjangoFilterBackend(BaseDjangoFilterBackend):
    search_param = "filter[search]"
