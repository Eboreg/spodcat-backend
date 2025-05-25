from django_filters import rest_framework as filters


class IdListFilter(filters.FilterSet):
    id = filters.CharFilter(method="filter_id")

    def filter_id(self, queryset, name, value):
        ids = value.split(",")
        return queryset.filter(id__in=ids)
