import json
import math
import os
import re
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Generator, TypedDict

from django.core.files.images import ImageFile
from django.db.models.fields.files import FieldFile, ImageFieldFile
from PIL import Image
from pydub import AudioSegment


class UserAgentDict(TypedDict):
    name: str
    pattern: str
    category: str | None
    description: str | None
    svg: str | None
    comments: str | None
    urls: list[str] | None
    examples: list[str] | None


user_agent_dict_cache: dict[str, list[UserAgentDict]] = {}


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


def get_useragent_dict(user_agent: str) -> tuple[str, UserAgentDict] | tuple[None, None]:
    basenames = [("bot", "bots"), ("app", "apps"), ("library", "libraries"), ("browser", "browsers")]
    for key, basename in basenames:
        for data in get_useragent_dicts(basename):
            if re.search(data["pattern"], user_agent):
                return key, data
    return None, None


def get_useragent_dicts(basename: str) -> list[UserAgentDict]:
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
