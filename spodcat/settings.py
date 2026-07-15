from typing import cast
from urllib.parse import urljoin

from django.conf import settings as django_settings
from django.core.signals import setting_changed
from django.urls import reverse

from spodcat.types import SettingsFileFieldDict, SettingsFileFieldKey, SpodcatSettingsDict


REST_FRAMEWORK_DEFAULTS = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

if django_settings.DEBUG:
    REST_FRAMEWORK_DEFAULTS["DEFAULT_RENDERER_CLASSES"] = [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ]
else:
    REST_FRAMEWORK_DEFAULTS["DEFAULT_RENDERER_CLASSES"] = [
        "rest_framework.renderers.JSONRenderer",
    ]

SPECTACULAR_DEFAULTS = {
    "COMPONENT_SPLIT_REQUEST": True,
}

SPODCAT_DEFAULTS: SpodcatSettingsDict = {
    "BACKEND_HOST": "http://localhost:8000/",
    "BACKEND_ROOT": "",
    "FILEFIELDS": {},
    "FRONTEND_ROOT_URL": "http://localhost:3000/",
    "STATIC_RSS_XML": True,
    "USE_INTERNAL_AUDIO_PROXY": False,
    "USE_INTERNAL_AUDIO_REDIRECT": False,
}


def patch_django_settings():
    django_settings.REST_FRAMEWORK = {**REST_FRAMEWORK_DEFAULTS, **getattr(django_settings, "REST_FRAMEWORK", {})}
    django_settings.SPECTACULAR_SETTINGS = {
        **SPECTACULAR_DEFAULTS,
        **getattr(django_settings, "SPECTACULAR_SETTINGS", {}),
    }


class SpodcatSettings:
    _user_settings: dict | None
    BACKEND_HOST: str | None
    BACKEND_ROOT: str | None
    FILEFIELDS: dict[SettingsFileFieldKey, SettingsFileFieldDict]
    FRONTEND_ROOT_URL: str | None
    STATIC_RSS_XML: bool
    USE_INTERNAL_AUDIO_PROXY: bool
    USE_INTERNAL_AUDIO_REDIRECT: bool

    def __init__(self, defaults: SpodcatSettingsDict | None = None):
        self._user_settings = None
        self.defaults = defaults or SPODCAT_DEFAULTS
        self._cached_attrs = set()

    @property
    def user_settings(self):
        if self._user_settings is None:
            self._user_settings = getattr(django_settings, "SPODCAT", {})
        return cast(SpodcatSettingsDict, self._user_settings)

    def __getattr__(self, attr):
        try:
            val = self.user_settings[attr]
        except KeyError:
            val = self.defaults[attr]

        self._cached_attrs.add(attr)
        setattr(self, attr, val)
        return val

    def get_absolute_backend_url(self, viewname: str, args=None, kwargs=None, query=None) -> str:
        return urljoin(self.get_backend_root_url(), reverse(viewname, args=args, kwargs=kwargs, query=query))

    def get_absolute_frontend_url(self, path: str) -> str:
        return urljoin(self.FRONTEND_ROOT_URL or "", path)

    def get_backend_root_path(self) -> str:
        """Only (absolute) path, without host."""
        root = (self.BACKEND_ROOT or "").strip("/")
        if root:
            return f"/{root}/"
        return "/"

    def get_backend_root_url(self) -> str:
        """Host and absolute path."""
        return (self.BACKEND_HOST or "").rstrip("/") + self.get_backend_root_path()

    def reload(self):
        for attr in self._cached_attrs:
            delattr(self, attr)
        self._cached_attrs.clear()
        self._user_settings = None


spodcat_settings = SpodcatSettings(SPODCAT_DEFAULTS)


def reload_spodcat_settings(*args, **kwargs):
    patch_django_settings()
    if kwargs["setting"] == "SPODCAT":
        spodcat_settings.reload()


setting_changed.connect(reload_spodcat_settings)
