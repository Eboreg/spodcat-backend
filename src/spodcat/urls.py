from django.urls import include, path
from rest_framework.routers import DefaultRouter

from spodcat.views import (
    ChallengeViewSet,
    CommentViewSet,
    EpisodeViewSet,
    PodcastLinkViewSet,
    PodcastViewSet,
    PostViewSet,
)
from spodcat.views.font_face import font_face_css


router = DefaultRouter()

router.register(prefix="challenges", viewset=ChallengeViewSet, basename="challenge")
router.register(prefix="comments", viewset=CommentViewSet, basename="comment")
router.register(prefix="episodes", viewset=EpisodeViewSet, basename="episode")
router.register(prefix="podcasts", viewset=PodcastViewSet, basename="podcast")
router.register(prefix="podcast-links", viewset=PodcastLinkViewSet, basename="podcast-link")
router.register(prefix="posts", viewset=PostViewSet, basename="post")


app_name = "spodcat"
urlpatterns = [
    path("", include(router.urls)),
    path("font-faces/", font_face_css),
]
