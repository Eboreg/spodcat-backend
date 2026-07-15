from rest_framework.mixins import CreateModelMixin, DestroyModelMixin
from rest_framework.viewsets import GenericViewSet

from spodcat import serializers
from spodcat.models import Challenge


class ChallengeViewSet(CreateModelMixin, DestroyModelMixin, GenericViewSet[Challenge]):
    serializer_class = serializers.ChallengeSerializer
    queryset = Challenge.objects.all()
