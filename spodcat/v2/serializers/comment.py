from rest_framework import serializers

from spodcat.models import Challenge, Comment
from spodcat.serializers.comment import CommentSerializerMixin


class CommentSerializer(CommentSerializerMixin, serializers.ModelSerializer[Comment]):
    challenge = serializers.PrimaryKeyRelatedField(queryset=Challenge.objects, write_only=True)
    challenge_answer = serializers.IntegerField(write_only=True)
    is_approved = serializers.BooleanField(read_only=True)
    text_html = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = "__all__"
