from rest_framework_json_api import views

from spodcat import serializers
from spodcat.filters import IdListFilter
from spodcat.models.podcast_link import PodcastLink
from spodcat.views.mixins import LogRequestMixin, PreloadIncludesMixin


class PodcastLinkViewSet(LogRequestMixin, PreloadIncludesMixin, views.ReadOnlyModelViewSet[PodcastLink]):
    queryset = PodcastLink.objects.all()
    filterset_class = IdListFilter
    serializer_class = serializers.PodcastLinkSerializer
