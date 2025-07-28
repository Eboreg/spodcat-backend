from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    RetrieveModelMixin,
)
from rest_framework.viewsets import GenericViewSet

from spodcat import serializers
from spodcat.models import Challenge


class ChallengeViewSet(CreateModelMixin, RetrieveModelMixin, DestroyModelMixin, GenericViewSet[Challenge]):
    select_for_includes = {
        "__all__": ["podcast"],
    }
    serializer_class = serializers.ChallengeSerializer

    def get_queryset(self, *args, **kwargs):
        return Challenge.objects.all()
