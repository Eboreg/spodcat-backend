from rest_framework import serializers

from spodcat.models import Video


class VideoSerializer(serializers.ModelSerializer[Video]):
    class Meta:
        exclude = ["podcast_content"]
        model = Video
