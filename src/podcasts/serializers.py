from urllib.parse import urljoin

from django.conf import settings
from django.urls import reverse
from rest_framework_json_api import serializers
from rest_framework_json_api.relations import ResourceRelatedField

from podcasts.models import Category, Episode, Podcast, PodcastLink


class PodcastLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = PodcastLink
        fields = "__all__"


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class PodcastSerializer(serializers.ModelSerializer):
    episodes = ResourceRelatedField(queryset=Episode.objects, many=True)
    links = ResourceRelatedField(queryset=PodcastLink.objects, many=True)
    rss_url = serializers.SerializerMethodField()
    description_html = serializers.SerializerMethodField()

    included_serializers = {
        "episodes": "podcasts.serializers.EpisodeSerializer",
        "owners": "users.serializers.UserSerializer",
        "categories": "podcasts.serializers.CategorySerializer",
        "links": "podcasts.serializers.PodcastLinkSerializer",
    }

    class Meta:
        model = Podcast
        fields = "__all__"

    def get_description_html(self, obj: Podcast):
        return obj.description_html

    def get_rss_url(self, obj: Podcast):
        return urljoin(settings.ROOT_URL, reverse("rss", kwargs={"slug": obj.slug}))


class EpisodeSerializer(serializers.ModelSerializer):
    description_html = serializers.SerializerMethodField()

    included_serializers = {
        "podcast": "podcasts.serializers.PodcastSerializer",
    }

    class Meta:
        model = Episode
        fields = "__all__"

    def get_description_html(self, obj: Episode):
        return obj.description_html
