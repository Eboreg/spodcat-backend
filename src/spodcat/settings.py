from urllib.parse import urljoin

from django.conf import settings
from django.core.signals import setting_changed
from django.urls import reverse


def get_lib_doc_excludes():
    from drf_spectacular.plumbing import (
        get_lib_doc_excludes as get_lib_doc_excludes_base,
    )
    from rest_framework_json_api import views

    return [
        *get_lib_doc_excludes_base(),
        *[getattr(views, c) for c in dir(views) if c.endswith("ViewSet") or c.endswith("View") or c.endswith("Mixin")],
    ]


REST_FRAMEWORK_DEFAULTS = {
    "EXCEPTION_HANDLER": "rest_framework_json_api.exceptions.exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_FILTER_BACKENDS": (
        "rest_framework_json_api.filters.QueryParameterValidationFilter",
        "rest_framework_json_api.filters.OrderingFilter",
        "rest_framework_json_api.django_filters.DjangoFilterBackend",
    ),
    "DEFAULT_METADATA_CLASS": "rest_framework_json_api.metadata.JSONAPIMetadata",
    "DEFAULT_PAGINATION_CLASS": "drf_spectacular_jsonapi.schemas.pagination.JsonApiPageNumberPagination",
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework_json_api.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser"
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework_json_api.renderers.JSONRenderer",
        "rest_framework_json_api.renderers.BrowsableAPIRenderer",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular_jsonapi.schemas.openapi.JsonApiAutoSchema",
    "PAGE_SIZE": None,
    "SEARCH_PARAM": "filter[search]",
}

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

DEFAULTS = {
    "BACKEND_HOST": "http://localhost:8000/",
    "BACKEND_ROOT": "",
    "FRONTEND_ROOT_URL": "http://localhost:4200/",
    "USE_INTERNAL_AUDIO_PROXY": False,
    "USE_INTERNAL_AUDIO_REDIRECT": False,
}


def patch_django_settings():
    for key, value in DJANGO_DEFAULTS.items():
        if not hasattr(settings, key):
            setattr(settings, key, value)

    settings.REST_FRAMEWORK = {**REST_FRAMEWORK_DEFAULTS, **getattr(settings, "REST_FRAMEWORK", {})}
    settings.SPECTACULAR_SETTINGS = {**SPECTACULAR_DEFAULTS, **getattr(settings, "SPECTACULAR_SETTINGS", {})}


class SpodcatSettings:
    _user_settings: dict | None = None

    def __init__(self, defaults: dict | None = None):
        self.defaults = defaults or DEFAULTS
        self._cached_attrs = set()

    @property
    def user_settings(self):
        user_settings = self._user_settings
        if user_settings is None:
            user_settings = getattr(settings, "SPODCAT", {})
            self._user_settings = user_settings
        return user_settings

    def __getattr__(self, attr):
        try:
            val = self.user_settings[attr]
        except KeyError:
            val = self.defaults[attr]

        self._cached_attrs.add(attr)
        setattr(self, attr, val)
        return val

    def get_absolute_backend_url(self, viewname: str, args=None, kwargs=None, query=None):
        return urljoin(self.get_backend_root_url(), reverse(viewname, args=args, kwargs=kwargs, query=query))

    def get_backend_root_path(self):
        """Only (absolute) path, without host."""
        root = self.BACKEND_ROOT.strip("/")
        if root:
            return f"/{root}/"
        return "/"

    def get_backend_root_url(self):
        """Host and absolute path."""
        return self.BACKEND_HOST.rstrip("/") + self.get_backend_root_path()

    def reload(self):
        for attr in self._cached_attrs:
            delattr(self, attr)
        self._cached_attrs.clear()
        self._user_settings = None


spodcat_settings = SpodcatSettings(DEFAULTS)


def reload_spodcat_settings(*args, **kwargs):
    patch_django_settings()
    if kwargs["setting"] == "SPODCAT":
        spodcat_settings.reload()


setting_changed.connect(reload_spodcat_settings)
