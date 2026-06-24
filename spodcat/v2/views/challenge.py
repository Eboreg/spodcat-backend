from rest_framework.mixins import CreateModelMixin, DestroyModelMixin
from rest_framework.viewsets import GenericViewSet

from spodcat.models import Challenge
from spodcat.v2.serializers.challenge import ChallengeSerializer

from .base import V2ViewMixin


class ChallengeViewSet(
    CreateModelMixin,
    V2ViewMixin,
    DestroyModelMixin,
    GenericViewSet[Challenge],
):
    serializer_class = ChallengeSerializer
    queryset = Challenge.objects.all()
