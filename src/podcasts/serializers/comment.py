from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.html import strip_tags
from rest_framework_json_api import serializers
from rest_framework_json_api.relations import PolymorphicResourceRelatedField

from podcasts.models import Challenge, Comment, PodcastContent
from podcasts.serializers.podcast_content import PodcastContentSerializer


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
        return value[:50]

    def validate_text(self, value: str):
        return strip_tags(value)
