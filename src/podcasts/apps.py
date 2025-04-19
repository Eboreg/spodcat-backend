from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class PodcastsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "podcasts"

    def ready(self):
        from podcasts import signals


class PodcastsAdminConfig(AdminConfig):
    default_site = "podcasts.admin_site.AdminSite"
