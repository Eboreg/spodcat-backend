from rest_framework_json_api import serializers

from users.models import User


class UserSerializer(serializers.ModelSerializer):
    included_serializers = {
        "podcasts": "podcasts.serializers.PodcastSerializer",
        "owned_podcasts": "podcasts.serializers.PodcastSerializer",
    }

    class Meta:
        fields = ("username", "first_name", "last_name", "email", "podcasts", "owned_podcasts")
        model = User
