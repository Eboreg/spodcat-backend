from django.db import models
from klaatu_django.db import TruncatedCharField
from rest_framework.request import Request


class AbstractRequestLog(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    remote_host = TruncatedCharField(max_length=100, blank=True)
    remote_addr = models.GenericIPAddressField(blank=True, null=True, max_length=50)
    user_agent = TruncatedCharField(max_length=200, blank=True)
    referer = TruncatedCharField(max_length=100, blank=True)
    path_info = TruncatedCharField(max_length=200, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.path_info

    @classmethod
    def create(cls, request: Request, **kwargs):
        return cls.objects.create(
            remote_host=request.META.get("REMOTE_HOST", ""),
            remote_addr=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.headers.get("User-Agent", ""),
            referer=request.headers.get("Referer", ""),
            path_info=request.path_info,
            **kwargs,
        )


class PodcastRequestLog(AbstractRequestLog):
    podcast = models.ForeignKey("podcasts.Podcast", on_delete=models.CASCADE)


class PodcastRssRequestLog(PodcastRequestLog):
    ...


class PodcastContentRequestLog(AbstractRequestLog):
    content = models.ForeignKey("podcasts.PodcastContent", on_delete=models.CASCADE)


class EpisodeAudioRequestLog(PodcastContentRequestLog):
    ...
