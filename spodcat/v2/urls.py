from django.urls import include, path
from rest_framework.routers import DefaultRouter

from spodcat.v2 import views


router = DefaultRouter()

router.register(prefix="challenges", viewset=views.ChallengeViewSet, basename="challenge")
router.register(prefix="comments", viewset=views.CommentViewSet, basename="comment")
router.register(prefix="episodes", viewset=views.EpisodeViewSet, basename="episode")
router.register(prefix="podcast-contents", viewset=views.PodcastContentViewSet, basename="podcast-content")
router.register(prefix="podcast-links", viewset=views.PodcastLinkViewSet, basename="podcast-link")
router.register(prefix="podcasts", viewset=views.PodcastViewSet, basename="podcast")
router.register(prefix="posts", viewset=views.PostViewSet, basename="post")
router.register(prefix="seasons", viewset=views.SeasonViewSet, basename="season")

app_name = "v2"
urlpatterns = [
    path("", include(router.urls)),
]
