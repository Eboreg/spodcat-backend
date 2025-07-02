from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    RetrieveModelMixin,
)
from rest_framework.viewsets import GenericViewSet

from spodcat import serializers
from spodcat.models import Challenge


class ChallengeViewSet(CreateModelMixin, RetrieveModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = Challenge.objects.select_related("podcast")
    serializer_class = serializers.ChallengeSerializer
