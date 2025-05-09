from rest_framework_json_api import serializers
from rest_framework_json_api.relations import (
    PolymorphicResourceRelatedField,
    ResourceRelatedField,
)

from podcasts.models import Comment, Episode, EpisodeSong
from podcasts.serializers.episode_song import EpisodeSongSerializer


class EpisodeSerializer(serializers.ModelSerializer):
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
        "comments": "podcasts.serializers.CommentSerializer",
        "podcast": "podcasts.serializers.PodcastSerializer",
        "songs": "podcasts.serializers.EpisodeSongSerializer",
    }

    class Meta:
        exclude = ["polymorphic_ctype"]
        model = Episode

    def get_audio_url(self, obj: Episode):
        return obj.audio_file.url if obj.audio_file else None

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
        ]
        model = Episode
