from django_filters import rest_framework as filters
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.viewsets import GenericViewSet

from spodcat import serializers
from spodcat.models import Comment


class CommentFilter(filters.FilterSet):
    podcast_content = filters.CharFilter(field_name="podcast_content")


class CommentViewSet(CreateModelMixin, ListModelMixin, GenericViewSet[Comment]):
    filterset_class = CommentFilter
    queryset = Comment.objects.filter(is_approved=True)
    serializer_class = serializers.CommentSerializer
