from rest_framework_json_api import views

from spodcat import serializers
from spodcat.filters import IdListFilter
from spodcat.models import PodcastLink


class PodcastLinkViewSet(views.ReadOnlyModelViewSet):
    filterset_class = IdListFilter
    queryset = PodcastLink.objects.all()
    select_for_includes = {
        "podcast": ["podcast"],
    }
    serializer_class = serializers.PodcastLinkSerializer
