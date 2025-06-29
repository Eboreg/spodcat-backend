from rest_framework_json_api import serializers

from spodcat.models import EpisodeSong


class EpisodeSongSerializer(serializers.ModelSerializer):
    included_serializers = {
        "artists": "spodcat.serializers.ArtistSerializer",
    }

    class Meta:
        fields = "__all__"
        model = EpisodeSong
