from rest_framework_json_api import serializers

from spodcat.models import PodcastContent

from .episode import EpisodeSerializer, PartialEpisodeSerializer
from .post import PartialPostSerializer, PostSerializer


class PodcastContentSerializer(serializers.PolymorphicModelSerializer[PodcastContent]):
    included_serializers = {
        "podcast": "spodcat.serializers.PodcastSerializer",
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
