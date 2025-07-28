from rest_framework.mixins import CreateModelMixin
from rest_framework_json_api import views

from spodcat import serializers
from spodcat.models import Comment


class CommentViewSet(CreateModelMixin, views.ReadOnlyModelViewSet[Comment]):
    serializer_class = serializers.CommentSerializer

    def get_queryset(self, *args, **kwargs):
        return Comment.objects.filter(is_approved=True)
