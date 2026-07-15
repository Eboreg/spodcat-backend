from rest_framework_json_api import serializers

from spodcat.models import Season


class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Season
        exclude = ["podcast"]
