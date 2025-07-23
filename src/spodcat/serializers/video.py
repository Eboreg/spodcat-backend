from rest_framework_json_api import serializers
from rest_framework_json_api.relations import PolymorphicResourceRelatedField

from spodcat.models import PodcastContent, Video

from .podcast_content import PodcastContentSerializer


class VideoSerializer(serializers.ModelSerializer[Video]):
    podcast_content = PolymorphicResourceRelatedField(PodcastContentSerializer, queryset=PodcastContent.objects)

    class Meta:
        fields = "__all__"
        model = Video
