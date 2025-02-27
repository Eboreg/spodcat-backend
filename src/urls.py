from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from podcasts.views import EpisodeViewSet, PodcastContentViewSet, PodcastViewSet, podcast_rss
from serve_media import serve_media
from users.views import UserViewSet


router = DefaultRouter()

router.register(prefix="users", viewset=UserViewSet, basename="user")
router.register(prefix="podcasts", viewset=PodcastViewSet, basename="podcast")
router.register(prefix="episodes", viewset=EpisodeViewSet, basename="episode")
router.register(prefix="contents", viewset=PodcastContentViewSet, basename="content")


urlpatterns = [
    path("", include(router.urls)),
    path("admin/", admin.site.urls),
    path("rss/<str:slug>/", view=podcast_rss, name="rss"),
    path("mdeditor/", include("mdeditor.urls")),
]
urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT, view=serve_media))
if settings.DEBUG:
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
