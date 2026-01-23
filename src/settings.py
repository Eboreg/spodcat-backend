import os
from pathlib import Path

from django.utils.translation import gettext_lazy as _

from spodcat.utils import env_boolean


# Build paths inside the project like this: BASE_DIR / 'subdir'.
SRC_DIR = Path(__file__).resolve().parent
BASE_DIR = SRC_DIR.parent
ENVIRONMENT = os.environ.get("ENVIRONMENT", "production")

ADMINS = [(os.environ.get("ADMIN_NAME", "Admin"), os.environ.get("ADMIN_EMAIL", "root@localhost"))]
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", ".localhost,127.0.0.1,[::1]").split(",")
DEBUG = env_boolean("DEBUG")
DJANGO_DB = os.environ.get("DJANGO_DB", ENVIRONMENT)
INTERNAL_IPS = "127.0.0.1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")


# Application definition
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.forms",
    "django_extensions",
    "rest_framework",
    "rest_framework_json_api",
    "polymorphic",
    "martor",
    "django_filters",
    "spodcat",
    "spodcat.logs",
    "spodcat.contrib.admin",
    "test_env",
    "drf_spectacular",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

try:
    # pylint: disable=unused-import
    import debug_toolbar

    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")
except ImportError:
    pass

ROOT_URLCONF = "urls"

X_FRAME_OPTIONS = "SAMEORIGIN"

TEMPLATES = [
    {
        "APP_DIRS": True,
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
            ],
            "debug": DEBUG,
        },
    },
]

FORM_RENDERER = "django.forms.renderers.TemplatesSetting"
WSGI_APPLICATION = "wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
DATABASES: dict[str, dict] = {
    "local": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
    "production": {
        "ENGINE": os.environ.get("PROD_SQL_ENGINE"),
        "HOST": os.environ.get("PROD_SQL_HOST"),
        "NAME": os.environ.get("PROD_SQL_DB"),
        "PASSWORD": os.environ.get("PROD_SQL_PASSWORD"),
        "USER": os.environ.get("PROD_SQL_USER"),
    },
}
DATABASES["default"] = DATABASES[DJANGO_DB].copy()


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/
# LANGUAGE_CODE = "en-us"
LANGUAGE_CODE = "sv"
LANGUAGES = [
    ("en", _("English")),
    ("sv", _("Swedish")),
]
LOCALE_PATHS = [SRC_DIR / "spodcat/locale"]
TIME_ZONE = "Europe/Stockholm"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/
# https://django-storages.readthedocs.io/en/latest/backends/azure.html
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"
STATIC_ROOT = BASE_DIR / "static"
STATIC_URL = "static/"
STATICFILES_DIRS = []

AZURE_ACCOUNT_KEY = os.environ.get("AZURE_FILES_KEY")
AZURE_ACCOUNT_NAME = os.environ.get("AZURE_ACCOUNT_NAME", "musikensmakt")
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET")
AZURE_CONTAINER = os.environ.get("AZURE_CONTAINER", "spodcat-backend")
AZURE_LOCATION = ENVIRONMENT
AZURE_RESOURCE_GROUP = os.environ.get("AZURE_RESOURCE_GROUP")
AZURE_SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID")
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID")

STORAGES = {
    "default": {"BACKEND": "storages.backends.azure_storage.AzureStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    "local": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
}


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django REST Framework
REST_FRAMEWORK = {
    "TEST_REQUEST_DEFAULT_FORMAT": "vnd.api+json",
    "TEST_REQUEST_RENDERER_CLASSES": (
        "rest_framework_json_api.renderers.JSONRenderer",
    ),
}


MARTOR_ENABLE_LABEL = True
AUTH_USER_MODEL = "test_env.User"


SPODCAT = {
    "BACKEND_HOST": os.environ.get("BACKEND_HOST"),
    "FILEFIELDS": {
        "FONTFACE_FILE": {"STORAGE": "local"},
    },
    "FRONTEND_ROOT_URL": os.environ.get("FRONTEND_ROOT_URL"),
    "USE_INTERNAL_AUDIO_REDIRECT": True,
}
