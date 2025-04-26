from rest_framework_json_api import serializers

from podcasts.models import Challenge


class ChallengeSerializer(serializers.ModelSerializer):
    challenge_string = serializers.SerializerMethodField()
    id = serializers.UUIDField(read_only=True)

    class Meta:
        fields = ["id", "challenge_string"]
        model = Challenge

    def get_challenge_string(self, obj: Challenge):
        return obj.challenge_string
