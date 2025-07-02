from django.apps import AppConfig


class SpodcatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "spodcat"

    def ready(self):
        from spodcat import signals
        from spodcat.settings import patch_django_settings

        patch_django_settings()
