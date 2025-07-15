from rest_framework_json_api import serializers
from rest_framework_json_api.relations import ResourceRelatedField

from spodcat.models import Challenge, Podcast


class ChallengeSerializer(serializers.ModelSerializer[Challenge]):
    challenge_string = serializers.SerializerMethodField()
    id = serializers.UUIDField(read_only=True)
    podcast = ResourceRelatedField(queryset=Podcast.objects)

    class Meta:
        fields = ["id", "challenge_string", "podcast"]
        model = Challenge

    def get_challenge_string(self, obj: Challenge):
        return obj.challenge_string
