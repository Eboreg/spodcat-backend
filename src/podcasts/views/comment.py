from rest_framework.mixins import CreateModelMixin
from rest_framework_json_api import views

from podcasts import serializers
from podcasts.models.comment import Comment


class CommentViewSet(CreateModelMixin, views.ReadOnlyModelViewSet):
    serializer_class = serializers.CommentSerializer
    queryset = Comment.objects.filter(is_approved=True)
