from rest_framework import serializers

from spodcat.models import PodcastLink


class PodcastLinkSerializer(serializers.ModelSerializer[PodcastLink]):
    class Meta:
        exclude = ["order"]
        model = PodcastLink
