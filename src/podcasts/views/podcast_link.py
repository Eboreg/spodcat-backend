from rest_framework_json_api import views

from podcasts import serializers
from podcasts.models import PodcastLink
from utils.filters import IdListFilter


class PodcastLinkViewSet(views.ReadOnlyModelViewSet):
    filterset_class = IdListFilter
    queryset = PodcastLink.objects.all()
    select_for_includes = {
        "podcast": ["podcast"],
    }
    serializer_class = serializers.PodcastLinkSerializer
