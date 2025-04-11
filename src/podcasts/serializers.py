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
    comments = ResourceRelatedField(queryset=Comment.objects, many=True)

    included_serializers = {
        "podcast": "podcasts.serializers.PodcastSerializer",
        "songs": "podcasts.serializers.EpisodeSongSerializer",
        "comments": "podcasts.serializers.CommentSerializer",
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
    comments = ResourceRelatedField(queryset=Comment.objects, many=True)

    included_serializers = {
        "podcast": "podcasts.serializers.PodcastSerializer",
        "comments": "podcasts.serializers.CommentSerializer",
    }

    class Meta:
        model = Post
        exclude = ["polymorphic_ctype"]

    def get_description_html(self, obj: Episode) -> str:
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


class CommentSerializer(serializers.ModelSerializer):
    is_approved = serializers.BooleanField(read_only=True)
    challenge = serializers.PrimaryKeyRelatedField(queryset=Challenge.objects, write_only=True)
    challenge_answer = serializers.IntegerField(write_only=True)
    podcast_content = PolymorphicResourceRelatedField(PodcastContentSerializer, queryset=PodcastContent.objects)
    text_html = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = "__all__"

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
        elif podcast_content.podcast.owner and podcast_content.podcast.owner.email:
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
        "authors": "users.serializers.UserSerializer",
        "categories": "podcasts.serializers.CategorySerializer",
        "links": "podcasts.serializers.PodcastLinkSerializer",
        "contents": "podcasts.serializers.PartialPodcastContentSerializer",
    }

    class Meta:
        model = Podcast
        fields = "__all__"

    def get_rss_url(self, obj: Podcast) -> str:
        return obj.rss_url

    def get_description_html(self, obj: Podcast) -> str:
        return obj.description_html


class ChallengeSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    challenge_string = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = ["id", "challenge_string"]

    def get_challenge_string(self, obj: Challenge):
        return obj.challenge_string
