from django.utils import timezone
from rest_framework.response import Response
from rest_framework_json_api import views

from logs.models import PodcastContentRequestLog
from podcasts import serializers
from podcasts.models import PodcastContent


class PodcastContentViewSet(views.ReadOnlyModelViewSet):
    serializer_class = serializers.PodcastContentSerializer
    select_for_includes = {
        "podcast": ["podcast"],
    }
    queryset = PodcastContent.objects.all()

    def filter_queryset(self, queryset):
        return super().filter_queryset(queryset).filter(published__lte=timezone.now(), is_draft=False)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        PodcastContentRequestLog.create(request=request, content=instance)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
