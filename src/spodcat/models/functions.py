from typing import TYPE_CHECKING

from django.conf import settings
from django.core.signals import setting_changed
from django.utils.module_loading import import_string


if TYPE_CHECKING:
    from spodcat.models import (
        AbstractEpisodeChapter,
        Episode,
        FontFace,
        Podcast,
        PodcastLink,
    )


__user_functions = {}


def __perform_import(val):
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


def __reload(*args, **kwargs):
    setting = kwargs["setting"]
    if setting == "SPODCAT":
        __user_functions.clear()


def __run_function(key: str, *args, **kwargs):
    if key not in __user_functions:
        __user_functions[key] = __perform_import(getattr(settings, "SPODCAT", {}).get(key, None))
    func = __user_functions[key]
    return func(*args, **kwargs) if func else None


setting_changed.connect(__reload)


def episode_audio_file_path(instance: "Episode", filename: str):
    return __run_function("EPISODE_AUDIO_FILE_PATH", instance, filename) \
        or f"{instance.podcast.slug}/episodes/{filename}"


def episode_chapter_image_path(instance: "AbstractEpisodeChapter", filename: str):
    return __run_function("EPISODE_CHAPTER_IMAGE_PATH", instance, filename) \
        or f"{instance.episode.podcast.slug}/images/episodes/{instance.episode.slug}/chapters/{filename}"


def episode_image_path(instance: "Episode", filename: str):
    return __run_function("EPISODE_IMAGE_PATH", instance, filename) \
        or f"{instance.podcast.slug}/images/episodes/{instance.slug}/{filename}"


def episode_image_thumbnail_path(instance: "Episode", filename: str):
    return __run_function("EPISODE_IMAGE_THUMBNAIL_PATH", instance, filename) \
        or f"{instance.podcast.slug}/images/episodes/{instance.slug}/{filename}"


def fontface_file_path(instance: "FontFace", filename: str):
    return __run_function("FONTFACE_FILE_PATH", instance, filename) or f"fonts/{filename}"


def podcast_banner_path(instance: "Podcast", filename: str):
    return __run_function("PODCAST_BANNER_PATH", instance, filename) or f"{instance.slug}/images/{filename}"


def podcast_cover_path(instance: "Podcast", filename: str):
    return __run_function("PODCAST_COVER_PATH", instance, filename) or f"{instance.slug}/images/{filename}"


def podcast_cover_thumbnail_path(instance: "Podcast", filename: str):
    return __run_function("PODCAST_COVER_THUMBNAIL_PATH", instance, filename) or f"{instance.slug}/images/{filename}"


def podcast_favicon_path(instance: "Podcast", filename: str):
    return __run_function("PODCAST_FAVICON_PATH", instance, filename) or f"{instance.slug}/images/{filename}"


def podcast_link_icon_path(instance: "PodcastLink", filename: str):
    return __run_function("PODCAST_LINK_ICON_PATH", instance, filename) \
        or f"{instance.podcast.slug}/images/links/{filename}"
