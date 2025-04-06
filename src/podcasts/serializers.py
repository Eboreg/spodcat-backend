from rest_framework_json_api import serializers
from rest_framework_json_api.relations import (
    PolymorphicResourceRelatedField,
    ResourceRelatedField,
)

from podcasts.models import (
    Artist,
    Category,
    Episode,
    EpisodeSong,
    Podcast,
    PodcastContent,
    PodcastLink,
    Post,
)


class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = "__all__"


class EpisodeSongSerializer(serializers.ModelSerializer):
    included_serializers = {
        "artists": "podcasts.serializers.ArtistSerializer",
    }

    class Meta:
        model = EpisodeSong
        fields = "__all__"


class EpisodeSerializer(serializers.ModelSerializer):
    description_html = serializers.SerializerMethodField()
    audio_url = serializers.SerializerMethodField()
    songs = PolymorphicResourceRelatedField(
        EpisodeSongSerializer,
        queryset=EpisodeSong.objects,
        many=True,
    )
    has_songs = serializers.SerializerMethodField()

    included_serializers = {
        "podcast": "podcasts.serializers.PodcastSerializer",
        "songs": "podcasts.serializers.EpisodeSongSerializer",
    }

    class Meta:
        model = Episode
        exclude = ["polymorphic_ctype"]

    def get_audio_url(self, obj: Episode):
        return obj.audio_url

    def get_description_html(self, obj: Episode):
        return obj.description_html

    def get_has_songs(self, obj: Episode):
        return obj.songs.exists()


class PartialEpisodeSerializer(EpisodeSerializer):
    class Meta:
        model = Episode
        fields = ["name", "podcast", "number", "published", "duration_seconds", "slug", "id", "audio_url", "has_songs"]


class PostSerializer(serializers.ModelSerializer):
    description_html = serializers.SerializerMethodField()

    included_serializers = {
        "podcast": "podcasts.serializers.PodcastSerializer",
    }

    class Meta:
        model = Post
        exclude = ["polymorphic_ctype"]

    def get_description_html(self, obj: Episode):
        return obj.description_html


class PartialPostSerializer(PostSerializer):
    class Meta:
        model = Post
        fields = ["name", "podcast", "published", "slug", "id"]


class PodcastContentSerializer(serializers.PolymorphicModelSerializer):
    polymorphic_serializers = [EpisodeSerializer, PostSerializer]
    included_serializers = {
        "podcast": "podcasts.serializers.PodcastSerializer",
    }

    class Meta:
        model = PodcastContent
        fields = "__all__"


class PartialPodcastContentSerializer(PodcastContentSerializer):
    polymorphic_serializers = [PartialEpisodeSerializer, PartialPostSerializer]

    class Meta:
        model = PodcastContent
        fields = ["name", "podcast", "published", "slug", "id"]


class PodcastLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = PodcastLink
        fields = "__all__"


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class PodcastSerializer(serializers.ModelSerializer):
    links = ResourceRelatedField(queryset=PodcastLink.objects, many=True)
    rss_url = serializers.SerializerMethodField()
    contents = PolymorphicResourceRelatedField(
        PartialPodcastContentSerializer,
        queryset=PodcastContent.objects,
        many=True,
    )
    description_html = serializers.SerializerMethodField()

    included_serializers = {
        "owners": "users.serializers.UserSerializer",
        "categories": "podcasts.serializers.CategorySerializer",
        "links": "podcasts.serializers.PodcastLinkSerializer",
        "contents": "podcasts.serializers.PartialPodcastContentSerializer",
    }

    class Meta:
        model = Podcast
        fields = "__all__"

    def get_rss_url(self, obj: Podcast):
        return obj.rss_url

    def get_description_html(self, obj: Podcast):
        return obj.description_html
