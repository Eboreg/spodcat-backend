from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    RetrieveModelMixin,
)
from rest_framework.viewsets import GenericViewSet

from podcasts import serializers
from podcasts.models import Challenge


class ChallengeViewSet(CreateModelMixin, RetrieveModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = Challenge.objects.all()
    serializer_class = serializers.ChallengeSerializer
