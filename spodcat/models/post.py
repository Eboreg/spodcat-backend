from django.utils.translation import gettext_lazy as _

from spodcat.models import PodcastContent


class Post(PodcastContent):
    season = None
    season_id = None

    class Meta:
        verbose_name = _("post")
        verbose_name_plural = _("posts")
