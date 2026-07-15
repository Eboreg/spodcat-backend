from collections.abc import Callable
from typing import TYPE_CHECKING

from django.core.signals import setting_changed
from django.utils.module_loading import import_string

from spodcat.settings import spodcat_settings
from spodcat.types import SettingsFileFieldKey


if TYPE_CHECKING:
    from django.core.files.storage import Storage
    from django.db.models import Model

    from spodcat.models import AbstractEpisodeChapter, Episode, FontFace, Podcast, PodcastLink, Season


__user_functions: dict[str, Callable[["Model", str], str] | None] = {}
__user_storages: dict[str, "Storage | None"] = {}


def __get_storage(key: SettingsFileFieldKey) -> "Storage":
    from django.core.files.storage import default_storage, storages

    if key not in __user_storages:
        user_storage = spodcat_settings.FILEFIELDS.get(key, {}).get("STORAGE")
        if isinstance(user_storage, str):
            user_storage = storages[user_storage]
        __user_storages[key] = user_storage

    return __user_storages[key] or default_storage


def __get_upload_to(key: SettingsFileFieldKey, instance: "Model", filename: str) -> str | None:
    if key not in __user_functions:
        user_function = spodcat_settings.FILEFIELDS.get(key, {}).get("UPLOAD_TO")
        if isinstance(user_function, str):
            user_function = import_string(user_function)
        __user_functions[key] = user_function

    func = __user_functions[key]

    return func(instance, filename) if func else None


def __reload(*args, **kwargs):
    setting = kwargs.get("setting")

    if setting == "SPODCAT":
        __user_functions.clear()
        __user_storages.clear()


setting_changed.connect(__reload)


def episode_audio_file_storage() -> "Storage":
    return __get_storage("EPISODE_AUDIO_FILE")


def episode_audio_file_upload_to(instance: "Episode", filename: str) -> str:
    return __get_upload_to("EPISODE_AUDIO_FILE", instance, filename) or f"{instance.podcast.slug}/episodes/{filename}"


def episode_chapter_image_storage() -> "Storage":
    return __get_storage("EPISODE_CHAPTER_IMAGE")


def episode_chapter_image_upload_to(instance: "AbstractEpisodeChapter", filename: str) -> str:
    return (
        __get_upload_to("EPISODE_CHAPTER_IMAGE", instance, filename)
        or f"{instance.episode.podcast.slug}/images/episodes/{instance.episode.slug}/chapters/{filename}"
    )


def episode_image_storage() -> "Storage":
    return __get_storage("EPISODE_IMAGE")


def episode_image_thumbnail_storage() -> "Storage":
    return __get_storage("EPISODE_IMAGE_THUMBNAIL")


def episode_image_thumbnail_upload_to(instance: "Episode", filename: str) -> str:
    return (
        __get_upload_to("EPISODE_IMAGE_THUMBNAIL", instance, filename)
        or f"{instance.podcast.slug}/images/episodes/{instance.slug}/{filename}"
    )


def episode_image_upload_to(instance: "Episode", filename: str) -> str:
    return (
        __get_upload_to("EPISODE_IMAGE", instance, filename)
        or f"{instance.podcast.slug}/images/episodes/{instance.slug}/{filename}"
    )


def fontface_file_storage() -> "Storage":
    return __get_storage("FONTFACE_FILE")


def fontface_file_upload_to(instance: "FontFace", filename: str) -> str:
    return __get_upload_to("FONTFACE_FILE", instance, filename) or f"fonts/{filename}"


def podcast_banner_storage() -> "Storage":
    return __get_storage("PODCAST_BANNER")


def podcast_banner_upload_to(instance: "Podcast", filename: str) -> str:
    return __get_upload_to("PODCAST_BANNER", instance, filename) or f"{instance.slug}/images/{filename}"


def podcast_cover_storage() -> "Storage":
    return __get_storage("PODCAST_COVER")


def podcast_cover_thumbnail_storage() -> "Storage":
    return __get_storage("PODCAST_COVER_THUMBNAIL")


def podcast_cover_thumbnail_upload_to(instance: "Podcast", filename: str) -> str:
    return __get_upload_to("PODCAST_COVER_THUMBNAIL", instance, filename) or f"{instance.slug}/images/{filename}"


def podcast_cover_upload_to(instance: "Podcast", filename: str) -> str:
    return __get_upload_to("PODCAST_COVER", instance, filename) or f"{instance.slug}/images/{filename}"


def podcast_favicon_storage() -> "Storage":
    return __get_storage("PODCAST_FAVICON")


def podcast_favicon_upload_to(instance: "Podcast", filename: str) -> str:
    return __get_upload_to("PODCAST_FAVICON", instance, filename) or f"{instance.slug}/images/{filename}"


def podcast_link_icon_storage() -> "Storage":
    return __get_storage("PODCAST_LINK_ICON")


def podcast_link_icon_upload_to(instance: "PodcastLink", filename: str) -> str:
    return (
        __get_upload_to("PODCAST_LINK_ICON", instance, filename) or f"{instance.podcast.slug}/images/links/{filename}"
    )


def rss_xml_storage() -> "Storage":
    return __get_storage("RSS_XML")


def season_image_storage() -> "Storage":
    return __get_storage("SEASON_IMAGE")


def season_image_thumbnail_storage() -> "Storage":
    return __get_storage("SEASON_IMAGE_THUMBNAIL")


def season_image_thumbnail_upload_to(instance: "Season", filename: str) -> str:
    return (
        __get_upload_to("SEASON_IMAGE_THUMBNAIL", instance, filename)
        or f"{instance.podcast.slug}/images/seasons/{instance.number}/{filename}"
    )


def season_image_upload_to(instance: "Season", filename: str) -> str:
    return (
        __get_upload_to("SEASON_IMAGE", instance, filename)
        or f"{instance.podcast.slug}/images/seasons/{instance.number}/{filename}"
    )
