from rest_framework.mixins import CreateModelMixin
from rest_framework_json_api import views

from podcasts import serializers
from podcasts.models import Comment


class CommentViewSet(CreateModelMixin, views.ReadOnlyModelViewSet):
    queryset = Comment.objects.filter(is_approved=True)
    serializer_class = serializers.CommentSerializer
