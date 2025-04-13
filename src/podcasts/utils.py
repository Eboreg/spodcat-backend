import json
import math
import os
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Generator, Literal, TypedDict

from django.core.files.images import ImageFile
from django.db.models.fields.files import FieldFile, ImageFieldFile
from PIL import Image
from pydub import AudioSegment


UserAgentType = Literal["bot", "app", "library", "browser"]


@dataclass
class UserAgentData:
    user_agent: str
    type: UserAgentType
    name: str
    is_bot: bool
    device_name: str | None = None
    device_category: Literal["smart_speaker", "mobile", "smart_tv", "watch", "computer", "auto"] | None = None
    referrer_name: str | None = None
    referrer_category: Literal["host", "app"] | None = None

    @classmethod
    # pylint: disable=redefined-builtin
    def from_dicts(
        cls,
        user_agent: str,
        type: UserAgentType,
        ua_dict: "UserAgentDict",
        device: "DeviceDict | None",
        referrer: "ReferrerDict | None",
    ):
        return cls(
            user_agent=user_agent,
            type=type,
            name=ua_dict["name"],
            is_bot=type == "bot" or ua_dict.get("category") == "bot",
            device_name=device["name"] if device else None,
            device_category=device["category"] if device else None,
            referrer_name=referrer["name"] if referrer else None,
            referrer_category=referrer["category"] if referrer else None,
        )


class BaseUserAgentDict(TypedDict):
    name: str
    pattern: str
    comments: str | None
    description: str | None
    examples: list[str] | None
    svg: str | None
    urls: list[str] | None


class UserAgentDict(BaseUserAgentDict):
    category: Literal["bot"] | None


class DeviceDict(BaseUserAgentDict):
    category: Literal["smart_speaker", "mobile", "smart_tv", "watch", "computer", "auto"]


class ReferrerDict(BaseUserAgentDict):
    category: Literal["host", "app"]


user_agent_dict_cache: dict[str, list] = {}


def delete_storage_file(file: FieldFile):
    if file:
        file.storage.delete(name=file.name)


def downscale_image(image: ImageFieldFile, max_width: int, max_height: int, save: bool = False):
    if image and image.width > max_width and image.height > max_height:
        buf = BytesIO()

        with Image.open(image) as im:
            ratio = max(max_width / im.width, max_height / im.height)
            im.thumbnail((int(im.width * ratio), int(im.height * ratio)))
            im.save(buf, format=im.format)

        image.save(name=image.name, content=ImageFile(file=buf), save=save)


def generate_thumbnail(from_field: ImageFieldFile, to_field: ImageFieldFile, size: int, save: bool = False):
    stem, suffix = os.path.splitext(os.path.basename(from_field.name))
    thumbnail_filename = f"{stem}-thumbnail{suffix}"
    buf = BytesIO()

    with Image.open(from_field) as im:
        ratio = size / max(im.width, im.height)
        im.thumbnail((int(im.width * ratio), int(im.height * ratio)))
        im.save(buf, format=im.format)
        mimetype = im.get_format_mimetype()

    to_field.save(name=thumbnail_filename, content=ImageFile(file=buf), save=save)
    return mimetype


def get_audio_file_dbfs_array(file: BinaryIO, format_name: str) -> list[float]:
    dbfs_values = [-100.0 if s.dBFS < -100 else s.dBFS for s in split_audio_file(file, 200, format_name)]
    min_dbfs = min(dbfs_values)
    dbfs_values = [dbfs - min_dbfs for dbfs in dbfs_values]
    max_dbfs = max(dbfs_values)
    multiplier = 100 / max_dbfs

    return [dbfs * multiplier for dbfs in dbfs_values]


def get_useragent_data(user_agent: str) -> UserAgentData | None:
    basenames: list[tuple[UserAgentType, str]] = [
        ("bot", "bots"),
        ("app", "apps"),
        ("library", "libraries"),
        ("browser", "browsers"),
    ]

    for key, basename in basenames:
        ua_dict: UserAgentDict | None = get_useragent_dict_from_file(basename, user_agent)
        if ua_dict:
            device: DeviceDict | None = get_useragent_dict_from_file("devices", user_agent) if key != "bot" else None
            referrer: ReferrerDict | None = (
                get_useragent_dict_from_file("referrers", user_agent)
                if key == "browser" else None
            )

            return UserAgentData.from_dicts(
                user_agent=user_agent,
                type=key,
                ua_dict=ua_dict,
                device=device,
                referrer=referrer,
            )

    return None


def get_useragent_dict_from_file(basename: str, user_agent: str):
    for ua_dict in get_useragent_dicts(basename):
        if re.search(ua_dict["pattern"], user_agent):
            return ua_dict
    return None


def get_useragent_dicts(basename: str):
    from podcasts import utils

    cached = utils.user_agent_dict_cache.get(basename, None)
    if cached is not None:
        return cached

    dicts = []
    json_path = (Path(__file__) / f"../../../user-agents-v2/src/{basename}.json").resolve()

    if json_path.is_file():
        with json_path.open("rt") as f:
            dicts = json.loads(f.read()).get("entries", [])

    utils.user_agent_dict_cache[basename] = dicts

    return dicts


def split_audio_file(file: BinaryIO, parts: int, format_name: str) -> Generator[AudioSegment, None, None]:
    whole = AudioSegment.from_file(file, format_name)
    i = 0
    n = math.ceil(len(whole) / parts)

    while i < len(whole):
        yield whole[i:i + n]
        i += n
