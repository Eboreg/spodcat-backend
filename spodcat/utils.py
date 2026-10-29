from __future__ import annotations

import datetime
import os
import re
from typing import TYPE_CHECKING

from django.utils.timezone import get_current_timezone, make_aware, now
from markdown import markdown

from spodcat.markdown import MarkdownExtension


if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile
    from django.http import HttpRequest
    from django.http.response import HttpResponseBase
    from rest_framework.request import Request


def date_to_datetime(date: datetime.date) -> datetime.datetime:
    return make_aware(datetime.datetime(date.year, date.month, date.day))


def date_to_timestamp_ms(date: datetime.date) -> int:
    epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    dt = datetime.datetime(date.year, date.month, date.day, tzinfo=get_current_timezone())

    return int((dt - epoch).total_seconds() * 1000)


def delete_storage_file(file: FieldFile) -> None:
    if file and file.name:
        file.storage.delete(name=file.name)


def env_boolean(key: str, default: bool = False) -> bool:
    if key in os.environ:
        return os.environ[key].lower() not in ("false", "no", "0")
    return default


def extract_range_request_header(request: Request | HttpRequest) -> tuple[int, int] | None:
    range_match = re.match(r"^bytes=(\d*)-(\d*)$", request.headers.get("Range", ""))

    if range_match and range_match.group(1) and range_match.group(2):
        return int(range_match.group(1)), int(range_match.group(2))

    return None


def markdown_to_html(md: str | None) -> str:
    if md:
        return markdown(md, extensions=["nl2br", "smarty", MarkdownExtension()])
    return ""


def round_to_whole_hour(d: datetime.datetime | None = None) -> datetime.datetime:
    d = d or now()
    return datetime.datetime(year=d.year, month=d.month, day=d.day, hour=d.hour, tzinfo=d.tzinfo)


def seconds_to_timestamp(value: int) -> str:
    hours = int(value / 60 / 60)
    minutes = int(value / 60 % 60)
    seconds = int(value % 60 % 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def set_range_response_headers(response: HttpResponseBase, range_start: int, range_end: int, total_size: int) -> None:
    response["Content-Range"] = f"bytes {range_start}-{range_end}/{total_size}"
    response["Content-Length"] = range_end - range_start
