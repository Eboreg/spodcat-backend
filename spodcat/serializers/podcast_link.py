from rest_framework_json_api import serializers

from spodcat.models import PodcastLink


class PodcastLinkSerializer(serializers.ModelSerializer):
    class Meta:
        exclude = ["order", "podcast"]
        model = PodcastLink
