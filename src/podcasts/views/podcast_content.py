from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_json_api import views

from logs.models import PodcastContentRequestLog
from podcasts import serializers
from podcasts.models import PodcastContent


class PodcastContentViewSet(views.ReadOnlyModelViewSet):
    queryset = PodcastContent.objects.all()
    select_for_includes = {
        "podcast": ["podcast"],
    }
    serializer_class = serializers.PodcastContentSerializer

    def filter_queryset(self, queryset):
        return super().filter_queryset(queryset).visible()

    @action(methods=["post"], detail=True)
    def ping(self, request: Request, pk: str):
        instance = self.get_object()
        PodcastContentRequestLog.create_from_request(request=request, content=instance)
        return Response()
