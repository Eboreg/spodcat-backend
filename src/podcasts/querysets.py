from django.utils import timezone
from polymorphic.query import PolymorphicQuerySet


class PodcastContentQuerySet(PolymorphicQuerySet):
    def partial(self):
        return self.only(
            "Episode___audio_file",
            "Episode___duration_seconds",
            "Episode___number",
            "Episode___podcastcontent_ptr_id",
            "name",
            "podcast",
            "polymorphic_ctype_id",
            "published",
            "slug",
        )

    def visible(self):
        return self.filter(published__lte=timezone.now(), is_draft=False)
