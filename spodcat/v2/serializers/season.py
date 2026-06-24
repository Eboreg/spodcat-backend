from rest_framework import serializers

from spodcat.models.season import Season


class SeasonSerializer(serializers.ModelSerializer[Season]):
    class Meta:
        model = Season
        fields = ["id", "name", "number", "image_thumbnail"]
