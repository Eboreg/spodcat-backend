from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SpodcatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "spodcat"
    verbose_name = _("podcasts")

    def ready(self):
        from spodcat import signals
        from spodcat.settings import patch_django_settings

        patch_django_settings()
