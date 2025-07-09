import time
from typing import NotRequired, TypedDict


class ChapterLocationDict(TypedDict):
    name: str
    geo: str
    osm: NotRequired[str]


class ChapterDict(TypedDict):
    startTime: int | float
    endTime: NotRequired[int | float]
    title: NotRequired[str]
    img: NotRequired[str]
    url: NotRequired[str]
    toc: NotRequired[bool]
    location: NotRequired[ChapterLocationDict]


class RssImage(TypedDict):
    href: str


class RssLink(TypedDict):
    rel: str | None
    type: str | None
    href: str
    length: NotRequired[str]


class RssTag(TypedDict):
    term: str
    scheme: str
    label: str | None


class RssAuthor(TypedDict):
    name: str
    email: NotRequired[str]


class RssFeed(TypedDict):
    title: str
    links: list[RssLink]
    description: str
    link: str
    language: str
    category: str
    image: RssImage
    podcast_guid: NotRequired[str]
    author: NotRequired[str]
    tags: NotRequired[list[RssTag]]
    authors: NotRequired[list[RssAuthor]]


class RssEntry(TypedDict):
    title: str
    itunes_episode: NotRequired[str]
    itunes_season: NotRequired[str]
    description: NotRequired[str]
    published_parsed: NotRequired[time.struct_time]
    itunes_duration: NotRequired[str | int | float]
    image: NotRequired[RssImage]
    links: NotRequired[list[RssLink]]


class Rss(TypedDict):
    feed: RssFeed
    entries: list[RssEntry]
