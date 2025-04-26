from rest_framework_json_api import serializers

from podcasts.models import PodcastContent
from podcasts.serializers.episode import (
    EpisodeSerializer,
    PartialEpisodeSerializer,
)
from podcasts.serializers.post import PartialPostSerializer, PostSerializer


class PodcastContentSerializer(serializers.PolymorphicModelSerializer):
    included_serializers = {
        "podcast": "podcasts.serializers.PodcastSerializer",
    }
    polymorphic_serializers = [EpisodeSerializer, PostSerializer]

    class Meta:
        fields = "__all__"
        model = PodcastContent


class PartialPodcastContentSerializer(PodcastContentSerializer):
    polymorphic_serializers = [PartialEpisodeSerializer, PartialPostSerializer]

    class Meta:
        fields = ["name", "podcast", "published", "slug", "id"]
        model = PodcastContent
