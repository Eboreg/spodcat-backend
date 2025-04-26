from rest_framework_json_api import serializers
from rest_framework_json_api.relations import ResourceRelatedField

from podcasts.models import Comment, Episode, Post


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
