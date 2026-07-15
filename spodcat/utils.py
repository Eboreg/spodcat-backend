import datetime
import os
import re
from contextlib import contextmanager
from io import BytesIO

from django.core.files.images import ImageFile
from django.db.models.fields.files import FieldFile, ImageFieldFile
from django.http import HttpRequest
from django.http.response import HttpResponseBase
from django.utils.timezone import get_current_timezone, make_aware, now
from markdown import markdown
from PIL import Image
from rest_framework.request import Request

from spodcat.markdown import MarkdownExtension


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

        with resize_image(image, max_width, max_height=max_height) as im:
            im.save(buf, format=im.format)

        assert image.name
        image.save(name=image.name, content=ImageFile(file=buf), save=save)


def env_boolean(key: str, default: bool = False):
    if key in os.environ:
        return os.environ[key].lower() not in ("false", "no", "0")
    return default


def extract_range_request_header(request: Request | HttpRequest) -> tuple[int, int] | None:
    range_match = re.match(r"^bytes=(\d*)-(\d*)$", request.headers.get("Range", ""))

    if range_match and range_match.group(1) and range_match.group(2):
        return int(range_match.group(1)), int(range_match.group(2))

    return None


def filter_values_not_null(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def generate_thumbnail(from_field: ImageFieldFile, to_field: ImageFieldFile, size: int, save: bool = False):
    assert from_field.name
    stem, suffix = os.path.splitext(os.path.basename(from_field.name))
    thumbnail_filename = f"{stem}-thumbnail{suffix}"
    buf = BytesIO()

    with resize_image(from_field, size) as im:
        im.save(buf, format=im.format)
        mimetype = im.get_format_mimetype()

    to_field.save(name=thumbnail_filename, content=ImageFile(file=buf), save=save)
    return mimetype


def markdown_to_html(md: str | None):
    if md:
        return markdown(md, extensions=["nl2br", "smarty", MarkdownExtension()])
    return ""


@contextmanager
def resize_image(image, max_width: int, max_height: int | None = None):
    if max_height is None:
        max_height = max_width
    with Image.open(image) as im:
        ratio = max(max_width / im.width, max_height / im.height)
        im.thumbnail((int(im.width * ratio), int(im.height * ratio)))
        yield im


def round_to_whole_hour(d: datetime.datetime | None = None) -> datetime.datetime:
    d = d or now()
    return datetime.datetime(year=d.year, month=d.month, day=d.day, hour=d.hour, tzinfo=d.tzinfo)


def seconds_to_timestamp(value: int):
    hours = int(value / 60 / 60)
    minutes = int(value / 60 % 60)
    seconds = int(value % 60 % 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def set_range_response_headers(response: HttpResponseBase, range_start: int, range_end: int, total_size: int):
    response["Content-Range"] = f"bytes {range_start}-{range_end}/{total_size}"
    response["Content-Length"] = range_end - range_start


def strip_markdown_images(md: str | None):
    # Basic stripping of Markdown image tags:
    if md:
        return re.sub(r"[\r\n]*!\[.*?\]\(.*?\)", "", md).strip()
    return ""
