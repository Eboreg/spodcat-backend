from typing import TYPE_CHECKING

from django.conf import settings
from django.core.files.storage import default_storage, storages
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
__user_storages = {}


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


def __get_storage(key: str):
    if key not in __user_storages:
        user_storage = getattr(settings, "SPODCAT", {}).get("STORAGES", {}).get(key, None)
        if isinstance(user_storage, str):
            user_storage = storages[user_storage]
        __user_storages[key] = user_storage
    return __user_storages[key] or default_storage


def __get_upload_to(key: str, *args, **kwargs):
    if key not in __user_functions:
        user_function = getattr(settings, "SPODCAT", {}).get("UPLOAD_TO", {}).get(key, None)
        __user_functions[key] = __perform_import(user_function)
    func = __user_functions[key]
    return func(*args, **kwargs) if func else None


setting_changed.connect(__reload)


def episode_audio_file_upload_to(instance: "Episode", filename: str):
    return __get_upload_to("EPISODE_AUDIO_FILE", instance, filename) \
        or f"{instance.podcast.slug}/episodes/{filename}"


def episode_audio_file_storage():
    return __get_storage("EPISODE_AUDIO_FILE")


def episode_chapter_image_upload_to(instance: "AbstractEpisodeChapter", filename: str):
    return __get_upload_to("EPISODE_CHAPTER_IMAGE", instance, filename) or \
        f"{instance.episode.podcast.slug}/images/episodes/{instance.episode.slug}/chapters/{filename}"


def episode_chapter_image_storage():
    return __get_storage("EPISODE_CHAPTER_IMAGE")


def episode_image_thumbnail_upload_to(instance: "Episode", filename: str):
    return __get_upload_to("EPISODE_IMAGE_THUMBNAIL", instance, filename) or \
        f"{instance.podcast.slug}/images/episodes/{instance.slug}/{filename}"


def episode_image_thumbnail_storage():
    return __get_storage("EPISODE_IMAGE_THUMBNAIL")


def episode_image_upload_to(instance: "Episode", filename: str):
    return __get_upload_to("EPISODE_IMAGE", instance, filename) or \
        f"{instance.podcast.slug}/images/episodes/{instance.slug}/{filename}"


def episode_image_storage():
    return __get_storage("EPISODE_IMAGE")


def fontface_file_upload_to(instance: "FontFace", filename: str):
    return __get_upload_to("FONTFACE_FILE", instance, filename) or f"fonts/{filename}"


def fontface_file_storage():
    return __get_storage("FONTFACE_FILE")


def podcast_banner_upload_to(instance: "Podcast", filename: str):
    return __get_upload_to("PODCAST_BANNER", instance, filename) or f"{instance.slug}/images/{filename}"


def podcast_banner_storage():
    return __get_storage("PODCAST_BANNER")


def podcast_cover_thumbnail_upload_to(instance: "Podcast", filename: str):
    return __get_upload_to("PODCAST_COVER_THUMBNAIL", instance, filename) or f"{instance.slug}/images/{filename}"


def podcast_cover_thumbnail_storage():
    return __get_storage("PODCAST_COVER_THUMBNAIL")


def podcast_cover_upload_to(instance: "Podcast", filename: str):
    return __get_upload_to("PODCAST_COVER", instance, filename) or f"{instance.slug}/images/{filename}"


def podcast_cover_storage():
    return __get_storage("PODCAST_COVER")


def podcast_favicon_upload_to(instance: "Podcast", filename: str):
    return __get_upload_to("PODCAST_FAVICON", instance, filename) or f"{instance.slug}/images/{filename}"


def podcast_favicon_storage():
    return __get_storage("PODCAST_FAVICON")


def podcast_link_icon_upload_to(instance: "PodcastLink", filename: str):
    return __get_upload_to("PODCAST_LINK_ICON", instance, filename) \
        or f"{instance.podcast.slug}/images/links/{filename}"


def podcast_link_icon_storage():
    return __get_storage("PODCAST_LINK_ICON")
