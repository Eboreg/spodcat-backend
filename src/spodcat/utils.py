import datetime
import math
import os
from io import BytesIO
from typing import BinaryIO, Generator

from django.core.files.images import ImageFile
from django.db.models.fields.files import FieldFile, ImageFieldFile
from django.utils.timezone import get_current_timezone, make_aware
from PIL import Image
from pydub import AudioSegment


class Month:
    date: datetime.date
    timestamp_ms: int

    def __init__(self, year: int | None = None, month: int | None = None):
        if year is None or month is None:
            today = datetime.date.today()
            year = today.year
            month = today.month
        self.date = datetime.date(year=year, month=month, day=1)
        self.timestamp_ms = date_to_timestamp_ms(self.date)

    def __repr__(self):
        return f"Month({self.date.year}-{self.date.month:02d})"

    def __add__(self, other):
        if isinstance(other, int):
            date = self.date
            for _ in range(other):
                if date.month == 12:
                    date = datetime.date(year=date.year + 1, month=1, day=1)
                else:
                    date = datetime.date(year=date.year, month=date.month + 1, day=1)
            return Month.from_date(date)
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, Month):
            if self.date.year < other.date.year:
                return True
            if self.date.year == other.date.year and self.date.month < other.date.month:
                return True
            return False
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, Month):
            return other.date.year == self.date.year and other.date.month == self.date.month
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, int):
            date = self.date
            for _ in range(other):
                if date.month == 1:
                    date = datetime.date(year=date.year - 1, month=12, day=1)
                else:
                    date = datetime.date(year=date.year, month=date.month - 1, day=1)
            return Month.from_date(date)

        if isinstance(other, Month):
            if other == self:
                return 0
            smallest = other if other < self else self
            largest = other if other > self else self
            months = 0
            while True:
                largest -= 1
                months += 1
                if largest == smallest:
                    return months

        return NotImplemented

    def range(self, steps) -> "Generator[Month]":
        for i in range(steps):
            yield self + i

    def range_until(self, other: "Month", inclusive: bool = True):
        if other > self:
            for i in range(other - self):
                yield self + i
            if inclusive:
                yield other
        elif other == self and inclusive:
            yield self

    @classmethod
    def from_date(cls, date: datetime.date):
        return cls(year=date.year, month=date.month)


def date_to_datetime(date: datetime.date) -> datetime.datetime:
    return make_aware(datetime.datetime(date.year, date.month, date.day))


def date_to_timestamp_ms(date: datetime.date) -> int:
    epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    dt = datetime.datetime(date.year, date.month, date.day, tzinfo=get_current_timezone())

    return int((dt - epoch).total_seconds() * 1000)


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


def env_boolean(key: str, default: bool = False):
    if key in os.environ:
        return os.environ[key].lower() not in ("false", "no", "0")
    return default


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
