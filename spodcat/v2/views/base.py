from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.openapi import AutoSchema
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer


class V2ViewMixin:
    filter_backends = [DjangoFilterBackend]
    pagination_class = None
    renderer_classes = [
        JSONRenderer,
        BrowsableAPIRenderer,
    ]
    parser_classes = [
        JSONParser,
        FormParser,
        MultiPartParser,
    ]
    schema = AutoSchema()
