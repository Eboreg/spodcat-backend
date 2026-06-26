from django.conf import settings
from django.urls import include, path
from rest_framework.routers import DefaultRouter, SimpleRouter

from spodcat import views


if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register(prefix="challenges", viewset=views.ChallengeViewSet, basename="challenge")
router.register(prefix="comments", viewset=views.CommentViewSet, basename="comment")
router.register(prefix="episodes", viewset=views.EpisodeViewSet, basename="episode")
router.register(prefix="podcast-links", viewset=views.PodcastLinkViewSet, basename="podcast-link")
router.register(prefix="podcasts", viewset=views.PodcastViewSet, basename="podcast")
router.register(prefix="posts", viewset=views.PostViewSet, basename="post")

app_name = "spodcat"
urlpatterns = [
    path("", include(router.urls)),
    path("font-faces/", views.font_face_css, name="font-faces"),
    path("graph/", views.GraphView.as_view(), name="graph"),
    path("v2/", include("spodcat.v2.urls")),
]
