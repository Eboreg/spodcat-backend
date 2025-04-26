from rest_framework_json_api import serializers

from podcasts.models.podcast_link import PodcastLink


class PodcastLinkSerializer(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        model = PodcastLink
