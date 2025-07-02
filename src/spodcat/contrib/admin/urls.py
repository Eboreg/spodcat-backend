from django.contrib import admin
from django.urls import include, path

from spodcat.contrib.admin.views import markdown_image_upload


urlpatterns = [
    path("", admin.site.urls),
    path("markdown-image-upload/", markdown_image_upload, name="markdown-image-upload"),
    path("martor/", include("martor.urls")),
]
