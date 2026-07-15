from rest_framework import serializers

from spodcat.models import Challenge


class ChallengeSerializer(serializers.ModelSerializer[Challenge]):
    challenge_string = serializers.SerializerMethodField()
    id = serializers.UUIDField(read_only=True)

    class Meta:
        fields = ["id", "challenge_string", "podcast"]
        model = Challenge

    def get_challenge_string(self, obj: Challenge) -> str:
        return obj.challenge_string
