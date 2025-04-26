from rest_framework_json_api import serializers

from podcasts.models import EpisodeSong


class EpisodeSongSerializer(serializers.ModelSerializer):
    included_serializers = {
        "artists": "podcasts.serializers.ArtistSerializer",
    }

    class Meta:
        fields = "__all__"
        model = EpisodeSong
