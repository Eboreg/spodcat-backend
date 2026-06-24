from django_filters import rest_framework as filters
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.viewsets import GenericViewSet

from spodcat.models import Comment
from spodcat.v2.serializers.comment import CommentSerializer

from .base import V2ViewMixin


class CommentFilter(filters.FilterSet):
    podcast_content = filters.CharFilter(field_name="podcast_content")


class CommentViewSet(CreateModelMixin, ListModelMixin, V2ViewMixin, GenericViewSet[Comment]):
    filterset_class = CommentFilter
    queryset = Comment.objects.filter(is_approved=True)
    serializer_class = CommentSerializer
