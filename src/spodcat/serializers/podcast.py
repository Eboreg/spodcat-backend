from rest_framework_json_api import serializers
from rest_framework_json_api.relations import (
    PolymorphicResourceRelatedField,
    ResourceRelatedField,
)

from spodcat.models import Podcast, PodcastContent, PodcastLink

from .podcast_content import PartialPodcastContentSerializer


class PodcastSerializer(serializers.ModelSerializer[Podcast]):
    contents = PolymorphicResourceRelatedField(
        PartialPodcastContentSerializer,
        queryset=PodcastContent.objects,
        many=True,
    )
    description_html = serializers.SerializerMethodField()
    episodes_fm_url = serializers.SerializerMethodField()
    links = ResourceRelatedField(queryset=PodcastLink.objects, many=True)
    rss_url = serializers.SerializerMethodField()
    name_font_family = serializers.SerializerMethodField()

    included_serializers = {
        "categories": "spodcat.serializers.CategorySerializer",
        "contents": "spodcat.serializers.PartialPodcastContentSerializer",
        "links": "spodcat.serializers.PodcastLinkSerializer",
    }

    class Meta:
        exclude = ["authors", "owner", "custom_guid"]
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
