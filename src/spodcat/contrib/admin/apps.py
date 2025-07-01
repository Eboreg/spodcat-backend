from django.contrib.admin import autodiscover
from django.contrib.admin.apps import SimpleAdminConfig


class SpodcatContribAdminConfig(SimpleAdminConfig):
    default = True
    default_site = "spodcat.contrib.admin.site.AdminSite"

    def ready(self):
        super().ready()
        autodiscover()
