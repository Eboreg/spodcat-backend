from rest_framework import serializers

from spodcat.models import Podcast

from .podcast_link import PodcastLinkSerializer


class PodcastSerializer(serializers.ModelSerializer[Podcast]):
    description_html = serializers.SerializerMethodField()
    episodes_fm_url = serializers.SerializerMethodField()
    links = PodcastLinkSerializer(many=True)
    rss_url = serializers.SerializerMethodField()
    name_font_family = serializers.SerializerMethodField()

    class Meta:
        exclude = ["categories", "authors", "owner", "custom_guid", "episode_rss_suffix", "itunes_type"]
        model = Podcast

    def get_description_html(self, obj: Podcast) -> str:
        return obj.description_html

    def get_episodes_fm_url(self, obj: Podcast) -> str:
        return obj.episodes_fm_url

    def get_name_font_family(self, obj: Podcast) -> str | None:
        if obj.name_font_face:
            return obj.name_font_face.name
        return None

    def get_rss_url(self, obj: Podcast) -> str:
        return obj.rss_url
