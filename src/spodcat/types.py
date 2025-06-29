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
