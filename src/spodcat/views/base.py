from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework_json_api import views
from rest_framework_json_api.filters import (
    OrderingFilter,
    QueryParameterValidationFilter,
)
from rest_framework_json_api.metadata import JSONAPIMetadata
from rest_framework_json_api.pagination import JsonApiPageNumberPagination
from rest_framework_json_api.parsers import JSONParser
from rest_framework_json_api.renderers import (
    BrowsableAPIRenderer,
    JSONRenderer,
)

from spodcat.filters import DjangoFilterBackend


class ReadOnlyModelViewSet(views.ReadOnlyModelViewSet):
    pagination_class = JsonApiPageNumberPagination
    authentication_classes = []
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer, BrowsableAPIRenderer]
    metadata_class = JSONAPIMetadata
    filter_backends = [QueryParameterValidationFilter, OrderingFilter, DjangoFilterBackend]
