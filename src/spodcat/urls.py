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


router = DefaultRouter()

router.register(prefix="challenges", viewset=ChallengeViewSet, basename="challenge")
router.register(prefix="comments", viewset=CommentViewSet, basename="comment")
router.register(prefix="episodes", viewset=EpisodeViewSet, basename="episode")
router.register(prefix="podcasts", viewset=PodcastViewSet, basename="podcast")
router.register(prefix="podcast-links", viewset=PodcastLinkViewSet, basename="podcast-link")
router.register(prefix="posts", viewset=PostViewSet, basename="post")


urlpatterns = [
    path("", include(router.urls)),
]
