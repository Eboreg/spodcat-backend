from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from spodcat.utils.serve_media import serve_media
from spodcat.views import (
    ChallengeViewSet,
    CommentViewSet,
    EpisodeViewSet,
    PodcastLinkViewSet,
    PodcastViewSet,
    PostViewSet,
)
from spodcat.views.admin import markdown_image_upload


router = DefaultRouter()

router.register(prefix="challenges", viewset=ChallengeViewSet, basename="challenge")
router.register(prefix="comments", viewset=CommentViewSet, basename="comment")
router.register(prefix="episodes", viewset=EpisodeViewSet, basename="episode")
router.register(prefix="podcasts", viewset=PodcastViewSet, basename="podcast")
router.register(prefix="podcast-links", viewset=PodcastLinkViewSet, basename="podcast-link")
router.register(prefix="posts", viewset=PostViewSet, basename="post")


urlpatterns = [
    path("", include(router.urls)),
    path("admin/", admin.site.urls),
    path("markdown-image-upload/", markdown_image_upload),
    path("martor/", include("martor.urls")),
]
urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT, view=serve_media))
