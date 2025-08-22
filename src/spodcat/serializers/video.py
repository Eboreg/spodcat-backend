from rest_framework_json_api import serializers

from spodcat.models import Video


class VideoSerializer(serializers.ModelSerializer[Video]):
    class Meta:
        exclude = ["podcast_content"]
        model = Video
