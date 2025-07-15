from rest_framework_json_api import serializers
from rest_framework_json_api.relations import (
    PolymorphicResourceRelatedField,
    ResourceRelatedField,
)

from spodcat.models import Comment, Episode, EpisodeSong

from .episode_song import EpisodeSongSerializer


class EpisodeSerializer(serializers.ModelSerializer[Episode]):
    audio_url = serializers.SerializerMethodField()
    comments = ResourceRelatedField(queryset=Comment.objects, many=True)
    description_html = serializers.SerializerMethodField()
    has_songs = serializers.SerializerMethodField()
    songs = PolymorphicResourceRelatedField(
        EpisodeSongSerializer,
        queryset=EpisodeSong.objects,
        many=True,
    )

    included_serializers = {
        "comments": "spodcat.serializers.CommentSerializer",
        "podcast": "spodcat.serializers.PodcastSerializer",
        "songs": "spodcat.serializers.EpisodeSongSerializer",
    }

    class Meta:
        exclude = ["polymorphic_ctype", "is_draft", "audio_file", "audio_file_length"]
        model = Episode

    def get_audio_url(self, obj: Episode):
        return obj.get_audio_file_url()

    def get_description_html(self, obj: Episode):
        return obj.description_html

    def get_has_songs(self, obj: Episode):
        if hasattr(obj, "has_songs"):
            return getattr(obj, "has_songs")
        return obj.songs.exists()


class PartialEpisodeSerializer(EpisodeSerializer):
    class Meta:
        fields = [
            "audio_url",
            "duration_seconds",
            "has_songs",
            "id",
            "name",
            "number",
            "podcast",
            "published",
            "season",
            "slug",
            "image_thumbnail",
        ]
        model = Episode
