from rest_framework_json_api import serializers
from rest_framework_json_api.relations import ResourceRelatedField

from spodcat.models import Comment, Episode, Post
from spodcat.models.video import Video


class PostSerializer(serializers.ModelSerializer[Post]):
    comments = ResourceRelatedField(queryset=Comment.objects, many=True)
    description_html = serializers.SerializerMethodField()
    videos = ResourceRelatedField(queryset=Video.objects, many=True)

    included_serializers = {
        "comments": "spodcat.serializers.CommentSerializer",
        "podcast": "spodcat.serializers.PodcastSerializer",
        "videos": "spodcat.serializers.VideoSerializer",
    }

    class Meta:
        exclude = ["polymorphic_ctype", "is_draft"]
        model = Post

    def get_description_html(self, obj: Episode) -> str:
        return obj.description_html


class PartialPostSerializer(PostSerializer):
    class Meta:
        fields = ["name", "podcast", "published", "slug", "id"]
        model = Post
