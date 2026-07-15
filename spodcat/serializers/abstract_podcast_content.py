from typing import TypeVar

from rest_framework import serializers

from spodcat.models import PodcastContent
from spodcat.serializers.video import VideoSerializer


_MT = TypeVar("_MT", bound=PodcastContent)


class AbstractPodcastContentSerializer(serializers.ModelSerializer[_MT]):
    description_html = serializers.SerializerMethodField()
    podcast_name = serializers.CharField(source="podcast.name")
    resourcetype = serializers.SerializerMethodField()
    videos = VideoSerializer(many=True)

    def get_description_html(self, obj: _MT) -> str:
        return obj.description_html

    def get_resourcetype(self, obj: _MT):
        assert obj._meta.object_name
        return obj._meta.object_name.lower()
