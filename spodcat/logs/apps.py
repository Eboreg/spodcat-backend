from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SpodcatLogsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "spodcat.logs"
    label = "spodcat_logs"
    verbose_name = _("logs")
