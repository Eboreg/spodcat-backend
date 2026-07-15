from typing import cast
from urllib.parse import urljoin

from django.conf import settings as django_settings
from django.core.signals import setting_changed
from django.urls import reverse

from spodcat.types import SettingsFileFieldDict, SettingsFileFieldKey, SpodcatSettingsDict


def get_lib_doc_excludes():
    from drf_spectacular.plumbing import get_lib_doc_excludes as get_lib_doc_excludes_base
    from rest_framework_json_api import views

    return [
        *get_lib_doc_excludes_base(),
        *[getattr(views, c) for c in dir(views) if c.endswith("ViewSet") or c.endswith("View") or c.endswith("Mixin")],
    ]


REST_FRAMEWORK_DEFAULTS = {
    "EXCEPTION_HANDLER": "rest_framework_json_api.exceptions.exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_FILTER_BACKENDS": [
        "rest_framework_json_api.filters.QueryParameterValidationFilter",
        "rest_framework_json_api.filters.OrderingFilter",
        "rest_framework_json_api.django_filters.DjangoFilterBackend",
    ],
    "DEFAULT_METADATA_CLASS": "rest_framework_json_api.metadata.JSONAPIMetadata",
    "DEFAULT_PAGINATION_CLASS": "drf_spectacular_jsonapi.schemas.pagination.JsonApiPageNumberPagination",
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework_json_api.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular_jsonapi.schemas.openapi.JsonApiAutoSchema",
    "PAGE_SIZE": None,
    "SEARCH_PARAM": "filter[search]",
}

if django_settings.DEBUG:
    REST_FRAMEWORK_DEFAULTS["DEFAULT_RENDERER_CLASSES"] = [
        "rest_framework_json_api.renderers.JSONRenderer",
        "rest_framework_json_api.renderers.BrowsableAPIRenderer",
    ]
else:
    REST_FRAMEWORK_DEFAULTS["DEFAULT_RENDERER_CLASSES"] = [
        "rest_framework_json_api.renderers.JSONRenderer",
    ]

DJANGO_DEFAULTS = {
    "JSON_API_FORMAT_FIELD_NAMES": "dasherize",
    "JSON_API_FORMAT_TYPES": "dasherize",
}

SPECTACULAR_DEFAULTS = {
    "COMPONENT_SPLIT_REQUEST": True,
    "GET_LIB_DOC_EXCLUDES": get_lib_doc_excludes,
    "PREPROCESSING_HOOKS": [
        "drf_spectacular_jsonapi.hooks.fix_nested_path_parameters",
    ],
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
    for key, value in DJANGO_DEFAULTS.items():
        if not hasattr(django_settings, key):
            setattr(django_settings, key, value)

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
