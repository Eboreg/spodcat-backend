from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from podcasts.views import (
    ChallengeViewSet,
    CommentViewSet,
    EpisodeViewSet,
    PodcastContentViewSet,
    PodcastViewSet,
    PostViewSet,
)
from podcasts.views.admin import markdown_image_upload
from serve_media import serve_media
from users.views import UserViewSet


router = DefaultRouter()

router.register(prefix="users", viewset=UserViewSet, basename="user")
router.register(prefix="podcasts", viewset=PodcastViewSet, basename="podcast")
router.register(prefix="episodes", viewset=EpisodeViewSet, basename="episode")
router.register(prefix="contents", viewset=PodcastContentViewSet, basename="content")
router.register(prefix="posts", viewset=PostViewSet, basename="post")
router.register(prefix="challenges", viewset=ChallengeViewSet, basename="challenge")
router.register(prefix="comments", viewset=CommentViewSet, basename="comment")


urlpatterns = [
    path("", include(router.urls)),
    path("admin/", admin.site.urls),
    path("martor/", include("martor.urls")),
    path("markdown-image-upload/", markdown_image_upload),
]
urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT, view=serve_media))

try:
    import debug_toolbar

    urlpatterns.append(path("__debug__/", include(debug_toolbar.urls)))
except ImportError:
    pass
