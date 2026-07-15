# Spodcat

This is the backend part of my podcast platform. It's designed to go along with [the frontend part](https://github.com/Eboreg/spodcat-frontend). It's built on Django REST Framework with a JSON:API implementation, but more on that later. The admin interface is just the regular Django admin with some minor tweakage. My own specific implementation is available in [this repo](https://github.com/Eboreg/podd-huseli-us-backend) and is also live [here](https://podd.huseli.us).

It's mainly made for my own specific purposes. Lately I have been making some effort to generalise stuff, in order to facilitate some potential wider use. But there's probably lots more that needs to be done to that end.

## External (non-Python) requirements

* [FFMpeg](https://ffmpeg.org/ffprobe.html), for constructing `Episode.dbfs_array` (used for audio visualization in frontend) as well as extracting other audio file info

## Spodcat configuration

Spodcat is configured using a `SPODCAT` dict in your Django settings module. Its type is specified by `spodcat.types.SpodcatSettingsDict`. These are the available settings:

### `BACKEND_HOST`

Used (along with `BACKEND_ROOT`, see below) for generating RSS feed URLs which are sent to the frontend, as well as some stuff in the admin. Default: `http://localhost:8000/`.

### `BACKEND_ROOT`

Set this is your backend installation is not at the URL root. Default: empty string.

### `FILEFIELDS`

Contains settings for various `FileField`s on different models, and govern where uploaded files will be stored and by which storage engine.

```python
SPODCAT = {
    "FILEFIELDS": {
        SettingsFileFieldKey: {
            "UPLOAD_TO": Callable[[Model, str], str] | str,
            "STORAGE": Storage | Callable[[], Storage] | str,
        },
    },
}
```
I.e. the `UPLOAD_TO` values represent `FileField.upload_to` callables or paths to them, and `STORAGE` represent the `storage` parameter of the same `FileField` (with the addition that they can also be strings, in which case the storage with this key in `django.core.files.storage.storages` will be used).

If `STORAGE` is not configured for any field, `django.core.files.storage.default_storage` will be used.

Here are the available values for `SettingsFileFieldKey` and the model types and default values for their `UPLOAD_TO` settings:

* `EPISODE_AUDIO_FILE`
  * Model: `Episode`
  * `UPLOAD_TO` default: `f"{instance.podcast.slug}/episodes/{filename}"`
* `EPISODE_CHAPTER_IMAGE`
  * Model: `AbstractEpisodeChapter`
  * `UPLOAD_TO` default: `f"{instance.episode.podcast.slug}/images/episodes/{instance.episode.slug}/chapters/{filename}"`
* `EPISODE_IMAGE`
  * Model: `Episode`
  * `UPLOAD_TO` default: `f"{instance.podcast.slug}/images/episodes/{instance.slug}/{filename}"`
* `EPISODE_IMAGE_THUMBNAIL`: Same as above
* `FONTFACE_FILE`
  * Model: `FontFace`
  * `UPLOAD_TO` default: `f"fonts/{filename}"`
* `PODCAST_BANNER`
  * Model: `Podcast`
  * `UPLOAD_TO` default: `f"{instance.slug}/images/{filename}"`
* `PODCAST_COVER`: Same as above
* `PODCAST_COVER_THUMBNAIL`: Same as above
* `PODCAST_FAVICON`: Same as above
* `PODCAST_LINK_ICON`
  * Model: `PodcastLink`
  * `UPLOAD_TO` default: `f"{instance.podcast.slug}/images/links/{filename}"`
* `RSS_XML`
  * Not connected to a model. This determines the storage engine that will deal with static RSS XML (if `STATIC_RSS_XML` is enabled).
  * `UPLOAD_TO`: not used
* `SEASON_IMAGE`
  * Model: `Season`
  * `UPLOAD_TO` default: `f"{instance.podcast.slug}/images/season/{instance.number}/{filename}"`
* `SEASON_IMAGE_THUMBNAIL`: Same as above

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

### `FRONTEND_ROOT_URL`

Mainly used for RSS feed generation and some places in the admin. Default: `http://localhost:4200/`.

### `STATIC_RSS_XML`

Whether to serve RSS feeds from static files (regenerated every time a relevant object is created/modified/deleted in admin) or generate them on the fly for every request. Default: `True`.

### `USE_INTERNAL_AUDIO_PROXY`

Like `USE_INTERNAL_AUDIO_REDIRECT` but more involved and with many potential downsides. Basically, when set to `True` it will make the `spodcat:episode-audio` view act as a full on proxy instead of just redirecting, i.e. it will fetch the audio file contents from your storage provider and serve them directly. You probably only want to use this if you store episode audio locally on the backend server, or if you _really_ want to be able to log partial episode downloads but your storage provider doesn't let you access request logs. With remote storage backends, it will probably add a bunch of overhead and generally make things a little worse for everyone.

Takes priority over `USE_INTERNAL_AUDIO_REDIRECT` if `True`.

### `USE_INTERNAL_AUDIO_REDIRECT`

If `True`, the episode API responses and RSS feeds will use the internal view `spodcat:episode-audio` (resolving to something like `https://example.com/episodes/<episode-id>/audio/`) for episode URLs instead of linking directly to whatever `episode.audio_file.url` returns. This view will then save a `PodcastEpisodeAudioRequestLog` entry (provided the `spodcat.logs` app is installed) and return a 302 (temporary) redirect to `episode.audio_file.url`.

Possible use cases for this:

* Your storage provider cannot reliably provide permanent, canonical episode URLs for some reason
* You want to save `PodcastEpisodeAudioRequestLog` logs but your storage provider doesn't let you access request logs

Note that the `spodcat:episode-audio` view has no way to log partial episode downloads, and will log every request as if it's for the entire audio file.

## Other Django settings

This is a bare minimum of apps you need to include in your project:

```python
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "spodcat",
]
```
However, this will _only_ be able to run the API. It will not allow you to use the admin or the Django REST Framework browsable API, or do any logging of web page visits and episode downloads. This is probably more like what you want:

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

## Used software

* [Django](https://www.djangoproject.com/)
* [Django REST Framework](https://www.django-rest-framework.org/)
* [Django REST Framework JSON:API](https://django-rest-framework-json-api.readthedocs.io/)
* [django-filter](https://django-filter.readthedocs.io/)
* [django-polymorphic](https://django-polymorphic.readthedocs.io/)
* [django-rest-polymorphic](https://github.com/denisorehovsky/django-rest-polymorphic)
* [drf-nested-routers](https://github.com/alanjds/drf-nested-routers)
* [drf-spectacular](https://drf-spectacular.readthedocs.io/)
* [country_list](https://github.com/bulv1ne/country_list/) (for making country codes more human readable in admin)
* [python-feedgen](https://feedgen.kiesow.be/) (for generating RSS feeds)
* [Feedparser](https://feedparser.readthedocs.io/) (for importing external RSS feeds)
* [Maxmind GeoIP2 Python API](https://github.com/maxmind/GeoIP2-python) (getting geo data for remote IPs, for logging purposes)
* [iso639-lang](https://github.com/LBeaudoux/iso639) (getting possible language choices for podcasts)
* [klaatu-django](https://github.com/Eboreg/klaatu-django) (my own collection of useful bits & bobs)
* [Markdownify](https://github.com/matthewwithanm/python-markdownify) (convert HTML to Markdown when importing RSS feeds)
* [Martor](https://github.com/agusmakmun/django-markdown-editor) (Markdown editor for admin)
* [Pillow](https://pillow.readthedocs.io/) (for automatic image thumbnail generation)
* [Dateutil](https://dateutil.readthedocs.io/) (for generating statistics graphs in admin)
* [Python Slugify](https://github.com/un33k/python-slugify) (generating slugs for podcast episodes/posts)
