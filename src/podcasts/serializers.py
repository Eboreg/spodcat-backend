from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.html import strip_tags
from rest_framework_json_api import serializers
from rest_framework_json_api.relations import (
    PolymorphicResourceRelatedField,
    ResourceRelatedField,
)

from podcasts.models import (
    Artist,
    Category,
    Challenge,
    Comment,
    Episode,
    EpisodeSong,
    Podcast,
    PodcastContent,
    PodcastLink,
    Post,
)


class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        model = Artist


class EpisodeSongSerializer(serializers.ModelSerializer):
    included_serializers = {
        "artists": "podcasts.serializers.ArtistSerializer",
    }

    class Meta:
        fields = "__all__"
        model = EpisodeSong


class EpisodeSerializer(serializers.ModelSerializer):
    audio_url = serializers.SerializerMethodField()
    comments = ResourceRelatedField(queryset=Comment.objects, many=True)
    description_html = serializers.SerializerMethodField()
    has_songs = serializers.SerializerMethodField()
    songs = PolymorphicResourceRelatedField(
        EpisodeSongSerializer,
        queryset=EpisodeSong.objects,
        many=True,
    )

    included_serializers = {
        "comments": "podcasts.serializers.CommentSerializer",
        "podcast": "podcasts.serializers.PodcastSerializer",
        "songs": "podcasts.serializers.EpisodeSongSerializer",
    }

    class Meta:
        exclude = ["polymorphic_ctype"]
        model = Episode

    def get_audio_url(self, obj: Episode):
        return obj.audio_file.url if obj.audio_file else None

    def get_description_html(self, obj: Episode):
        return obj.description_html

    def get_has_songs(self, obj: Episode):
        return obj.songs.exists()


class PartialEpisodeSerializer(EpisodeSerializer):
    class Meta:
        fields = ["name", "podcast", "number", "published", "duration_seconds", "slug", "id", "audio_url", "has_songs"]
        model = Episode


class PostSerializer(serializers.ModelSerializer):
    comments = ResourceRelatedField(queryset=Comment.objects, many=True)
    description_html = serializers.SerializerMethodField()

    included_serializers = {
        "comments": "podcasts.serializers.CommentSerializer",
        "podcast": "podcasts.serializers.PodcastSerializer",
    }

    class Meta:
        exclude = ["polymorphic_ctype"]
        model = Post

    def get_description_html(self, obj: Episode) -> str:
        return obj.description_html


class PartialPostSerializer(PostSerializer):
    class Meta:
        fields = ["name", "podcast", "published", "slug", "id"]
        model = Post


class PodcastContentSerializer(serializers.PolymorphicModelSerializer):
    included_serializers = {
        "podcast": "podcasts.serializers.PodcastSerializer",
    }
    polymorphic_serializers = [EpisodeSerializer, PostSerializer]

    class Meta:
        fields = "__all__"
        model = PodcastContent


class CommentSerializer(serializers.ModelSerializer):
    challenge = serializers.PrimaryKeyRelatedField(queryset=Challenge.objects, write_only=True)
    challenge_answer = serializers.IntegerField(write_only=True)
    is_approved = serializers.BooleanField(read_only=True)
    podcast_content = PolymorphicResourceRelatedField(PodcastContentSerializer, queryset=PodcastContent.objects)
    text_html = serializers.SerializerMethodField()

    class Meta:
        fields = "__all__"
        model = Comment

    def get_text_html(self, obj: Comment):
        return obj.text_html

    def validate(self, attrs):
        challenge = attrs.pop("challenge", None)
        answer = attrs.pop("challenge_answer", None)
        podcast_content = attrs.get("podcast_content", None)

        assert isinstance(podcast_content, PodcastContent)
        assert isinstance(challenge, Challenge)

        if answer != challenge.term1 + challenge.term2:
            raise serializers.ValidationError({"challenge_answer": "Svaret är ej korrekt."})

        if not podcast_content.podcast.enable_comments:
            raise serializers.ValidationError("Podden stödjer ej kommentarer")

        if not podcast_content.podcast.require_comment_approval:
            attrs["is_approved"] = True
        elif podcast_content.podcast.owner.email:
            admin_url = urljoin(settings.ROOT_URL, reverse("admin:podcasts_comment_changelist")) + \
                f"?is_approved__exact=0&podcast_content__podcast__slug__exact={podcast_content.podcast.slug}"
            email_text = f"You have a new comment for {podcast_content.podcast.name} awaiting approval. " + \
                f"Look here: {admin_url}"
            send_mail(
                from_email=None,
                subject=f"Comment for {podcast_content.podcast.name} needs approval",
                message=email_text,
                recipient_list=[podcast_content.podcast.owner.email],
            )

        challenge.delete()
        return attrs

    def validate_name(self, value: str):
        return value[:100]

    def validate_text(self, value: str):
        return strip_tags(value)


class PartialPodcastContentSerializer(PodcastContentSerializer):
    polymorphic_serializers = [PartialEpisodeSerializer, PartialPostSerializer]

    class Meta:
        fields = ["name", "podcast", "published", "slug", "id"]
        model = PodcastContent


class PodcastLinkSerializer(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        model = PodcastLink


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        model = Category


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


class ChallengeSerializer(serializers.ModelSerializer):
    challenge_string = serializers.SerializerMethodField()
    id = serializers.UUIDField(read_only=True)

    class Meta:
        fields = ["id", "challenge_string"]
        model = Challenge

    def get_challenge_string(self, obj: Challenge):
        return obj.challenge_string
