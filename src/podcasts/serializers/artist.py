from rest_framework_json_api import serializers

from podcasts.models import Artist


class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        model = Artist
