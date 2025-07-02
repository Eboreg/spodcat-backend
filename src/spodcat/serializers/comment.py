from urllib.parse import urljoin

from django.core.mail import send_mail
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.translation import gettext as _
from rest_framework_json_api import serializers
from rest_framework_json_api.relations import PolymorphicResourceRelatedField

from spodcat.models import Challenge, Comment, PodcastContent
from spodcat.settings import spodcat_settings

from .podcast_content import PodcastContentSerializer


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
            raise serializers.ValidationError({"challenge_answer": _("The answer is not correct.")})

        if not podcast_content.podcast.enable_comments:
            raise serializers.ValidationError(_("This podcast does not support comments"))

        if not podcast_content.podcast.require_comment_approval:
            attrs["is_approved"] = True
            if podcast_content.podcast.owner.email:
                email_text = _(
                    "A new comment for %(podcast)s was just posted by %(name)s. Check it out here: %(url)s"
                ) % {
                    "podcast": podcast_content.podcast.name,
                    "name": attrs.get("name"),
                    "url": podcast_content.frontend_url,
                }
                send_mail(
                    from_email=None,
                    subject=_("Comment for %(podcast)s posted") % {"podcast": podcast_content.podcast.name},
                    message=email_text,
                    recipient_list=[podcast_content.podcast.owner.email],
                )
        elif podcast_content.podcast.owner.email:
            admin_url = urljoin(spodcat_settings.ROOT_URL, reverse("admin:podcasts_comment_changelist")) + \
                f"?is_approved__exact=0&podcast_content__podcast__slug__exact={podcast_content.podcast.slug}"
            email_text = _("You have a new comment for %(podcast)s awaiting approval. Look here: %(url)s") % {
                "podcast": podcast_content.podcast.name,
                "url": admin_url,
            }
            send_mail(
                from_email=None,
                subject=_("Comment for %(podcast)s needs approval") % {"podcast": podcast_content.podcast.name},
                message=email_text,
                recipient_list=[podcast_content.podcast.owner.email],
            )

        challenge.delete()
        return attrs

    def validate_name(self, value: str):
        return value[:50]

    def validate_text(self, value: str):
        return strip_tags(value)
