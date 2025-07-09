import datetime
import math
import os
from io import BytesIO
from typing import TYPE_CHECKING

from django.core.files.images import ImageFile
from django.db.models.fields.files import FieldFile, ImageFieldFile
from django.utils.timezone import get_current_timezone, make_aware
from PIL import Image
from pydub import AudioSegment


if TYPE_CHECKING:
    from tempfile import _TemporaryFileWrapper
    from typing import BinaryIO, Generator


def date_to_datetime(date: datetime.date) -> datetime.datetime:
    return make_aware(datetime.datetime(date.year, date.month, date.day))


def date_to_timestamp_ms(date: datetime.date) -> int:
    epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    dt = datetime.datetime(date.year, date.month, date.day, tzinfo=get_current_timezone())

    return int((dt - epoch).total_seconds() * 1000)


def delete_storage_file(file: FieldFile):
    if file and file.name:
        file.storage.delete(name=file.name)


def downscale_image(image: ImageFieldFile, max_width: int, max_height: int, save: bool = False):
    if image and image.width > max_width and image.height > max_height:
        buf = BytesIO()

        with Image.open(image) as im:
            ratio = max(max_width / im.width, max_height / im.height)
            im.thumbnail((int(im.width * ratio), int(im.height * ratio)))
            im.save(buf, format=im.format)

        assert image.name
        image.save(name=image.name, content=ImageFile(file=buf), save=save)


def env_boolean(key: str, default: bool = False):
    if key in os.environ:
        return os.environ[key].lower() not in ("false", "no", "0")
    return default


def filter_values_not_null(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def generate_thumbnail(from_field: ImageFieldFile, to_field: ImageFieldFile, size: int, save: bool = False):
    assert from_field.name
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


def get_audio_file_dbfs_array(file: "BinaryIO | _TemporaryFileWrapper[bytes]", format_name: str) -> list[float]:
    audio = AudioSegment.from_file(file, format_name)
    return get_audio_segment_dbfs_array(audio)


def get_audio_segment_dbfs_array(audio: AudioSegment) -> list[float]:
    dbfs_values = [-100.0 if s.dBFS < -100 else s.dBFS for s in split_audio_segment(audio, 200)]
    min_dbfs = min(dbfs_values)
    dbfs_values = [dbfs - min_dbfs for dbfs in dbfs_values]
    max_dbfs = max(dbfs_values)
    multiplier = 100 / max_dbfs

    return [dbfs * multiplier for dbfs in dbfs_values]


def seconds_to_timestamp(value: int):
    hours = int(value / 60 / 60)
    minutes = int(value / 60 % 60)
    seconds = int(value % 60 % 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def split_audio_segment(whole: AudioSegment, parts: int) -> "Generator[AudioSegment]":
    i = 0
    n = math.ceil(len(whole) / parts)

    while i < len(whole):
        part = whole[i:i + n]
        assert isinstance(part, AudioSegment)
        yield part
        i += n
