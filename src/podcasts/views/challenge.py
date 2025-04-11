from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from podcasts import serializers
from podcasts.models.challenge import Challenge


class ChallengeViewSet(CreateModelMixin, RetrieveModelMixin, GenericViewSet):
    serializer_class = serializers.ChallengeSerializer
    queryset = Challenge.objects.all()
