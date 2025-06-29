from django.conf import settings
from django.core.signals import setting_changed
from django.utils.module_loading import import_string


DEFAULTS = {
    "REST_FRAMEWORK": {
        "EXCEPTION_HANDLER": "rest_framework_json_api.exceptions.exception_handler",
        "DEFAULT_AUTHENTICATION_CLASSES": [],
        "DEFAULT_PAGINATION_CLASS":
            "rest_framework_json_api.pagination.JsonApiPageNumberPagination",
        "DEFAULT_PARSER_CLASSES": (
            "rest_framework_json_api.parsers.JSONParser",
            "rest_framework.parsers.FormParser",
            "rest_framework.parsers.MultiPartParser"
        ),
        "DEFAULT_RENDERER_CLASSES": (
            "rest_framework_json_api.renderers.JSONRenderer",
            "rest_framework_json_api.renderers.BrowsableAPIRenderer",
        ),
        "DEFAULT_METADATA_CLASS": "rest_framework_json_api.metadata.JSONAPIMetadata",
        "DEFAULT_FILTER_BACKENDS": (
            "rest_framework_json_api.filters.QueryParameterValidationFilter",
            "rest_framework_json_api.filters.OrderingFilter",
            "rest_framework_json_api.django_filters.DjangoFilterBackend",
        ),
        "SEARCH_PARAM": "filter[search]",
    },
    "JSON_API": {
        "JSON_API_FORMAT_FIELD_NAMES": "dasherize",
        "JSON_API_FORMAT_TYPES": "dasherize",
    },
    "FRONTEND_ROOT_URL": "http://localhost:4200/",
    "ROOT_URL": "http://localhost:8000/",
}


def perform_import(val):
    """
    If the given setting is a string import notation,
    then perform the necessary import or imports.
    """
    if val is None:
        return None
    if isinstance(val, str):
        return import_string(val)
    if isinstance(val, (list, tuple)):
        return [import_string(item) for item in val]
    return val


class SpodcatSettings:
    _user_settings: dict | None = None

    def __init__(self, defaults: dict | None = None):
        self.defaults = defaults or DEFAULTS
        self._cached_attrs = set()
        self.handle_jsonapi_settings()
        self.handle_rest_framework_settings()

    @property
    def user_settings(self):
        if self._user_settings is None:
            self._user_settings = getattr(settings, "SPODCAT", {})
        return self._user_settings

    def __getattr__(self, attr):
        try:
            val = self.user_settings[attr]
        except KeyError:
            val = self.defaults[attr]

        self._cached_attrs.add(attr)
        setattr(self, attr, val)
        return val

    def handle_jsonapi_settings(self):
        for key, value in self.defaults.get("JSON_API", {}).items():
            if not hasattr(settings, key):
                setattr(settings, key, value)

    def handle_rest_framework_settings(self):
        user_settings = {**self.user_settings.get("REST_FRAMEWORK", {}), **getattr(settings, "REST_FRAMEWORK", {})}
        for key, value in self.defaults.get("REST_FRAMEWORK", {}).items():
            if key not in user_settings:
                user_settings[key] = value
        setattr(settings, "REST_FRAMEWORK", user_settings)

    def reload(self):
        for attr in self._cached_attrs:
            delattr(self, attr)
        self._cached_attrs.clear()
        self._user_settings = None


spodcat_settings = SpodcatSettings(DEFAULTS)


def reload_spodcat_settings(*args, **kwargs):
    setting = kwargs["setting"]
    if setting == "SPODCAT":
        spodcat_settings.reload()


setting_changed.connect(reload_spodcat_settings)
