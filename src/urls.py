from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from spodcat.serve_media import serve_media


urlpatterns = [
    path("", include("spodcat.urls")),
    path("admin/", include("spodcat.contrib.admin.urls")),
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT, view=serve_media),
    *static(settings.STATIC_URL, document_root=settings.STATIC_ROOT),
]

try:
    import debug_toolbar

    urlpatterns.append(path("__debug__/", include(debug_toolbar.urls)))
except ImportError:
    pass
