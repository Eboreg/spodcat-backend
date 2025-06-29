import datetime
import math
import os
from io import BytesIO
from typing import Any, BinaryIO, Generator, Iterable

from django.core.files.images import ImageFile
from django.db.models.fields.files import FieldFile, ImageFieldFile
from django.utils import timezone
from PIL import Image
from pydub import AudioSegment


def date_to_datetime(date: datetime.date) -> datetime.datetime:
    return timezone.make_aware(datetime.datetime(date.year, date.month, date.day))


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


def filter_values_not_null(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


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
    audio = AudioSegment.from_file(file, format_name)
    return get_audio_segment_dbfs_array(audio)


def get_audio_segment_dbfs_array(audio: AudioSegment) -> list[float]:
    dbfs_values = [-100.0 if s.dBFS < -100 else s.dBFS for s in split_audio_segment(audio, 200)]
    min_dbfs = min(dbfs_values)
    dbfs_values = [dbfs - min_dbfs for dbfs in dbfs_values]
    max_dbfs = max(dbfs_values)
    multiplier = 100 / max_dbfs

    return [dbfs * multiplier for dbfs in dbfs_values]


def group_dicts(dicts: Iterable[dict[str, Any]], keys: list[str], data_key: str = "data") -> list[dict[str, Any]]:
    """
    In:
        dicts = [
            {"slug": "musikensmakt", "name": "Musikens Makt", "date": "2025-04-01", "count": 60},
            {"slug": "musikensmakt", "name": "Musikens Makt", "date": "2025-04-02", "count": 64},
            {"slug": "apanap", "name": "Apan Ap", "date": "2025-04-01", "count": 2},
        ]
        keys = ["slug", "name"]
        data_key = "dätä"
    Out: [
        {
            "slug": "musikensmakt",
            "name": "Musikens Makt",
            "dätä": [{"date": "2025-04-01", "count": 60}, {"date": "2025-04-02", "count": 64}],
        },
        {
            "slug": "apanap",
            "name": "Apan Ap",
            "dätä": [{"date": "2025-04-01", "count": 2}],
        },
    ]
    """
    result: dict[set[str], list] = {}

    for d in dicts:
        dd = d.copy()
        d_key = tuple(d[key] for key in keys)
        if d_key not in result:
            result[d_key] = []
        for key in keys:
            del dd[key]
        result[d_key].append(dd)

    return [{data_key: v, **{keys[i]: k[i] for i in range(len(keys))}} for k, v in result.items()]


def seconds_to_timestamp(value: int):
    hours = int(value / 60 / 60)
    minutes = int(value / 60 % 60)
    seconds = int(value % 60 % 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def split_audio_segment(whole: AudioSegment, parts: int) -> "Generator[AudioSegment]":
    i = 0
    n = math.ceil(len(whole) / parts)

    while i < len(whole):
        yield whole[i:i + n]
        i += n
