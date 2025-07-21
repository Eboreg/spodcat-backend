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
    queryset = Challenge.objects.all()
    serializer_class = serializers.ChallengeSerializer
