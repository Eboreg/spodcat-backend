# Spodcat

## Spodcat configuration

Spodcat is configured using a `SPODCAT` dict in your Django settings module. These are the available settings:

* `FRONTEND_ROOT_URL`: Mainly used for RSS feed generation and some places in the admin. Default: `http://localhost:4200/`
* `BACKEND_HOST`: Used (along with `BACKEND_ROOT`, see below) for generating RSS feed URLs which are sent to the frontend, as well as some stuff in the admin. Default: `http://localhost:8000/`
* `BACKEND_ROOT`: Set this is your backend installation is not at the URL root. Default: empty string
* `FILEFIELDS`: Described below.

`FILEFIELDS` contains settings for various `FileField`s on different models, and govern where uploaded files will be stored and by which storage engine.

```python
SPODCAT = {
    "FILEFIELDS": {
        "__FILEFIELD_CONSTANT__": {
            "UPLOAD_TO": Callable[[Model, str], str] | str,
            "STORAGE": Storage | Callable[[], Storage] | str,
        },
    },
}
```
I.e. the `UPLOAD_TO` values represent `FileField.upload_to` callables or paths to them, and `STORAGE` represent the `storage` parameter of the same `FileField` (with the addition that they can also be strings, in which case the storage with this key in `django.core.files.storage.storages` will be used).

Here are the available values for `__FILEFIELD_CONSTANT__` and the model types and default values for their `UPLOAD_TO` settings:

* `EPISODE_AUDIO_FILE`: Model is `Episode`. Default: `f"{instance.podcast.slug}/episodes/{filename}"`
* `EPISODE_CHAPTER_IMAGE`: Model is `AbstractEpisodeChapter`. Default: `f"{instance.episode.podcast.slug}/images/episodes/{instance.episode.slug}/chapters/{filename}"`
* `EPISODE_IMAGE`: Model is `Episode`. Default: `f"{instance.podcast.slug}/images/episodes/{instance.slug}/{filename}"`
* `EPISODE_IMAGE_THUMBNAIL`: Same as above
* `FONTFACE_FILE`: Model is `FontFace`. Default: `f"fonts/{filename}"`
* `PODCAST_BANNER`: Model is `Podcast`. Default: `f"{instance.slug}/images/{filename}"`
* `PODCAST_COVER`: Same as above
* `PODCAST_COVER_THUMBNAIL`: Same as above
* `PODCAST_FAVICON`: Same as above
* `PODCAST_LINK_ICON`: Model is `PodcastLink`. Default: `f"{instance.podcast.slug}/images/links/{filename}"`

Footnote: The reason for adding the `STORAGE` settings was that I did my file hosting with Azure, but that didn't work with CSS fonts since I couldn't control the `Access-Control-Allow-Origin` header. So I did this:

```python
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", BASE_DIR / "media")
MEDIA_URL = "/media/"

STORAGES = {
    "default": {"BACKEND": "storages.backends.azure_storage.AzureStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    "local": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
}

SPODCAT = {
    "FILEFIELDS": {
        "FONTFACE_FILE": {"STORAGE": "local"},
    },
    ...
}
```
... and then just had my web server reply to `MEDIA_URL` request by serving the files in `MEDIA_ROOT`.

## Other Django settings

This is a bare minimum of apps you need to include in your project:

```python
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "spodcat",
]
```
However, this will _only_ be able to run the API. It will not allow you to use the admin or the Django REST Framework browsable API. This is probably more like what you want:

```python
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",      # needed for admin
    "django.contrib.messages",      # needed for admin
    "django.contrib.staticfiles",   # needed for admin and REST browsable API
    "rest_framework",               # needed for REST browsable API
    "rest_framework_json_api",      # needed for REST browsable API
    "django_filters",               # needed for REST browsable API
    "martor",                       # needed for admin
    "spodcat",
    "spodcat.logs",
    "spodcat.contrib.admin",
]
```
Here, `spodcat.contrib.admin` is used instead of `django.contrib.admin`. It adds some nice stuff like a couple of charts and a notice on the admin index page about comments awaiting approval.

If you somehow don't want to log any page, episode audio, and RSS requests, you can leave out `spodcat.logs`.

## URLs

This root URL conf is perfectly adequate:

```python
from django.urls import include, path

urlpatterns = [
    path("", include("spodcat.urls")),
    path("admin/", include("spodcat.contrib.admin.urls")),
]
```
(You don't need to include `django.contrib.admin.site.urls` if you use `spodcat.contrib.admin.urls`.)
