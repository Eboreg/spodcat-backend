from spodcat.models import Post

from .abstract_podcast_content import AbstractPodcastContentSerializer


class PostSerializer(AbstractPodcastContentSerializer[Post]):
    class Meta:
        exclude = ["polymorphic_ctype", "is_draft"]
        model = Post


class PartialPostSerializer(PostSerializer):
    class Meta:
        fields = [
            "id",
            "name",
            "podcast",
            "published",
            "resourcetype",
            "slug",
        ]
        model = Post
