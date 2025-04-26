from rest_framework_json_api import serializers
from rest_framework_json_api.relations import (
    PolymorphicResourceRelatedField,
    ResourceRelatedField,
)

from podcasts.models import Podcast, PodcastContent, PodcastLink
from podcasts.serializers.podcast_content import (
    PartialPodcastContentSerializer,
)


class PodcastSerializer(serializers.ModelSerializer):
    contents = PolymorphicResourceRelatedField(
        PartialPodcastContentSerializer,
        queryset=PodcastContent.objects,
        many=True,
    )
    description_html = serializers.SerializerMethodField()
    links = ResourceRelatedField(queryset=PodcastLink.objects, many=True)
    rss_url = serializers.SerializerMethodField()

    included_serializers = {
        "authors": "users.serializers.UserSerializer",
        "categories": "podcasts.serializers.CategorySerializer",
        "contents": "podcasts.serializers.PartialPodcastContentSerializer",
        "links": "podcasts.serializers.PodcastLinkSerializer",
    }

    class Meta:
        fields = "__all__"
        model = Podcast

    def get_description_html(self, obj: Podcast) -> str:
        return obj.description_html

    def get_rss_url(self, obj: Podcast) -> str:
        return obj.rss_url
