from rest_framework import serializers

from spodcat.models import Episode

from .abstract_podcast_content import AbstractPodcastContentSerializer
from .episode_song import EpisodeSongSerializer


class EpisodeSerializer(AbstractPodcastContentSerializer[Episode]):
    audio_url = serializers.SerializerMethodField()
    has_songs = serializers.SerializerMethodField()
    season = serializers.PrimaryKeyRelatedField(read_only=True)
    songs = EpisodeSongSerializer(many=True)

    class Meta:
        exclude = ["polymorphic_ctype", "is_draft", "audio_file", "audio_file_length", "audio_content_type"]
        model = Episode

    def get_audio_url(self, obj: Episode) -> str | None:
        return obj.get_audio_file_url()

    def get_has_songs(self, obj: Episode) -> bool:
        if hasattr(obj, "has_songs"):
            return obj.has_songs  # type: ignore
        return obj.songs.exists()


class PartialEpisodeSerializer(EpisodeSerializer):
    class Meta:
        fields = [
            "audio_url",
            "duration_seconds",
            "has_songs",
            "id",
            "image_thumbnail",
            "name",
            "number",
            "podcast",
            "published",
            "resourcetype",
            "season",
            "slug",
        ]
        model = Episode
