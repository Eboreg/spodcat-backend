import os
from pathlib import Path

from django.utils.translation import gettext_lazy as _


def env_boolean(key: str):
    return key in os.environ and os.environ[key].lower() not in ("false", "no", "0")


# Build paths inside the project like this: BASE_DIR / 'subdir'.
SRC_DIR = Path(__file__).resolve().parent
BASE_DIR = SRC_DIR.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
DEBUG = env_boolean("DEBUG")
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", ".localhost,127.0.0.1,[::1]").split(",")
INTERNAL_IPS = os.environ.get("INTERNAL_IPS", "127.0.0.1").split(",")


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
    "spodcat.admin_site.SpodcatAdminConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "spodcat.urls"

X_FRAME_OPTIONS = "SAMEORIGIN"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [SRC_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": DEBUG,
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

FORM_RENDERER = "django.forms.renderers.TemplatesSetting"
WSGI_APPLICATION = "wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES: dict[str, dict] = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Stockholm"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [SRC_DIR / "spodcat/locale"]


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
# https://django-storages.readthedocs.io/en/latest/backends/azure.html
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static"


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django REST Framework
REST_FRAMEWORK = {
    "TEST_REQUEST_RENDERER_CLASSES": (
        "rest_framework_json_api.renderers.JSONRenderer",
    ),
    "TEST_REQUEST_DEFAULT_FORMAT": "vnd.api+json",
}

JSON_API_FORMAT_FIELD_NAMES = "dasherize"
JSON_API_FORMAT_TYPES = "dasherize"


# martor
MARTOR_ENABLE_LABEL = True
MARTOR_UPLOAD_URL = "/markdown-image-upload/"


# logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "spodcat.logging.AdminEmailHandler",
            "include_html": True,
            "filters": ["require_debug_false"],
        },
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "loggers": {
        "django.security.DisallowedHost": {
            "handlers": ["null"],
            "propagate": False,
        },
        "django": {
            "handlers": ["console", "mail_admins"],
            "level": "INFO",
        },
        "logs": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "podcasts": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "pydub.converter": {
            "handlers": ["console"],
            "level": "DEBUG",
        }
    },
}


# Own stuff
FRONTEND_ROOT_URL = os.environ.get("FRONTEND_ROOT_URL")
ROOT_URL = os.environ.get("ROOT_URL")

def episode_audio_file_path(instance, filename):
    return f"{instance.podcast.slug}/bög/{filename}"

SPODCAT = {
    "EPISODE_AUDIO_FILE_PATH": episode_audio_file_path,
    "FRONTEND_ROOT_URL": os.environ.get("FRONTEND_ROOT_URL"),
    "ROOT_URL": os.environ.get("ROOT_URL"),
}
