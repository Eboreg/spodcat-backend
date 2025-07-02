from django.contrib.admin import autodiscover
from django.contrib.admin.apps import SimpleAdminConfig
from django.urls.exceptions import NoReverseMatch


class SpodcatContribAdminConfig(SimpleAdminConfig):
    default = True
    default_site = "spodcat.contrib.admin.site.AdminSite"

    def ready(self):
        super().ready()
        autodiscover()
        self.patch_django_settings()

    def patch_django_settings(self):
        import martor.settings
        from django.conf import settings
        from django.urls import reverse

        if not hasattr(settings, "MARTOR_UPLOAD_URL"):
            try:
                url = reverse("markdown-image-upload")
                settings.MARTOR_UPLOAD_URL = url
                martor.settings.MARTOR_UPLOAD_URL = url
            except NoReverseMatch:
                pass
        if not hasattr(settings, "MARTOR_ENABLE_LABEL"):
            settings.MARTOR_ENABLE_LABEL = True
            martor.settings.MARTOR_ENABLE_LABEL = True
