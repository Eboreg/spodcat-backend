from rest_framework_json_api import serializers

from spodcat.models import Artist


class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        model = Artist
