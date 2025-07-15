from rest_framework_json_api import serializers

from spodcat.models.podcast_link import PodcastLink


class PodcastLinkSerializer(serializers.ModelSerializer[PodcastLink]):
    class Meta:
        exclude = ["order"]
        model = PodcastLink
