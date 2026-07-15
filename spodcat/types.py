from collections.abc import Callable
from typing import TYPE_CHECKING, Literal, NotRequired, TypedDict


if TYPE_CHECKING:
    from time import struct_time

    from django.core.files.storage import Storage
    from django.db.models import Model


class CategoryDict(TypedDict):
    cat: str
    sub: NotRequired[str]


class ChapterLocationDict(TypedDict):
    geo: str
    name: str
    osm: NotRequired[str]


class ChapterDict(TypedDict):
    endTime: NotRequired[int | float]
    img: NotRequired[str]
    location: NotRequired[ChapterLocationDict]
    startTime: int | float
    title: NotRequired[str]
    toc: NotRequired[bool]
    url: NotRequired[str]


class RssImage(TypedDict):
    href: str


class RssLink(TypedDict):
    href: str
    length: NotRequired[str]
    rel: str | None
    type: str | None


class RssTag(TypedDict):
    label: str | None
    scheme: str
    term: str


class RssAuthor(TypedDict):
    email: NotRequired[str]
    name: str


class RssFeed(TypedDict):
    author: NotRequired[str]
    authors: NotRequired[list[RssAuthor]]
    category: str
    description: str
    image: RssImage
    language: str
    link: str
    links: list[RssLink]
    podcast_guid: NotRequired[str]
    tags: NotRequired[list[RssTag]]
    title: str


class RssEntry(TypedDict):
    description: NotRequired[str]
    image: NotRequired[RssImage]
    itunes_duration: NotRequired[str | int | float]
    itunes_episode: NotRequired[str]
    itunes_season: NotRequired[str]
    links: NotRequired[list[RssLink]]
    published_parsed: NotRequired["struct_time"]
    title: str


class Rss(TypedDict):
    entries: list[RssEntry]
    feed: RssFeed


class SettingsFileFieldDict(TypedDict, total=False):
    STORAGE: "Storage | str"
    UPLOAD_TO: Callable[["Model", str], str] | str


SettingsFileFieldKey = Literal[
    "EPISODE_AUDIO_FILE",
    "EPISODE_CHAPTER_IMAGE",
    "EPISODE_IMAGE_THUMBNAIL",
    "EPISODE_IMAGE",
    "FONTFACE_FILE",
    "PODCAST_BANNER",
    "PODCAST_COVER_THUMBNAIL",
    "PODCAST_COVER",
    "PODCAST_FAVICON",
    "PODCAST_LINK_ICON",
    "RSS_XML",
    "SEASON_IMAGE_THUMBNAIL",
    "SEASON_IMAGE",
]


class SpodcatSettingsDict(TypedDict, total=False):
    BACKEND_HOST: str | None
    BACKEND_ROOT: str | None
    FILEFIELDS: dict[SettingsFileFieldKey, SettingsFileFieldDict]
    FRONTEND_ROOT_URL: str | None
    STATIC_RSS_XML: bool
    USE_INTERNAL_AUDIO_PROXY: bool
    USE_INTERNAL_AUDIO_REDIRECT: bool
