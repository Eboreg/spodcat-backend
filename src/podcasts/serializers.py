from urllib.parse import urljoin

from django.conf import settings
from django.urls import reverse
from rest_framework_json_api import serializers
from rest_framework_json_api.relations import (
    PolymorphicResourceRelatedField,
    ResourceRelatedField,
)

from podcasts.models import (
    Category,
    Episode,
    Podcast,
    PodcastContent,
    PodcastLink,
    Post,
)


class EpisodeSerializer(serializers.ModelSerializer):
    description_html = serializers.SerializerMethodField()
    audio_url = serializers.SerializerMethodField()

    included_serializers = {
        "podcast": "podcasts.serializers.PodcastSerializer",
    }

    class Meta:
        model = Episode
        exclude = ["polymorphic_ctype"]

    def get_audio_url(self, obj: Episode):
        return urljoin(settings.ROOT_URL, reverse("episode-audio", args=(obj.slug,)))

    def get_description_html(self, obj: Episode):
        return obj.description_html


class PartialEpisodeSerializer(EpisodeSerializer):
    class Meta:
        model = Episode
        fields = ["name", "podcast", "number", "published", "duration_seconds", "audio_file", "slug", "audio_url"]


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
        fields = ["name", "podcast", "published", "slug"]


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
        fields = ["name", "podcast", "published", "slug"]


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
        return urljoin(settings.ROOT_URL, reverse("podcast-rss", args=(obj.slug,)))

    def get_description_html(self, obj: Podcast):
        return obj.description_html
