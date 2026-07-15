from rest_framework import serializers

from spodcat.models import EpisodeSong
from spodcat.serializers.artist import ArtistSerializer


class EpisodeSongSerializer(serializers.ModelSerializer[EpisodeSong]):
    artists = ArtistSerializer(many=True)

    class Meta:
        exclude = ["episode"]
        model = EpisodeSong
