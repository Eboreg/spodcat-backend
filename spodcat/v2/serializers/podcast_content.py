from rest_polymorphic.serializers import PolymorphicSerializer

from spodcat.models import Episode, Post

from .episode import PartialEpisodeSerializer
from .post import PartialPostSerializer


class PodcastContentPolymorphicSerializer(PolymorphicSerializer):
    model_serializer_mapping = {
        Episode: PartialEpisodeSerializer,
        Post: PartialPostSerializer,
    }

    def to_resource_type(self, model_or_instance):
        return model_or_instance._meta.object_name.lower()
