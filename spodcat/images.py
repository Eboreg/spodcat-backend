from __future__ import annotations

import dataclasses
import os
import re
from collections.abc import Generator
from contextlib import contextmanager
from io import BytesIO
from typing import TYPE_CHECKING

from django.core.files.images import ImageFile
from feedgen.util import xml_elem
from PIL import Image, ImageOps


if TYPE_CHECKING:
    from django.db.models.fields.files import ImageFieldFile
    from PIL.ImageFile import ImageFile as PILImageFile


@dataclasses.dataclass
class ImageData:
    href: str
    width: int | None = None
    height: int | None = None
    type: str | None = None

    @property
    def aspect_ratio(self) -> float | None:
        if self.width and self.height:
            return self.width / self.height
        return None

    def create_xml_elem(self, parent, namespace):
        # https://podcasting2.org/docs/podcast-namespace/tags/image
        elem = xml_elem("{%s}image" % namespace, parent)
        elem.attrib["href"] = self.href

        if self.width:
            elem.attrib["width"] = str(self.width)
        if self.height:
            elem.attrib["height"] = str(self.height)
        if self.aspect_ratio:
            elem.attrib["aspect-ratio"] = str(self.aspect_ratio)
        if self.type:
            elem.attrib["type"] = self.type

        return elem


def downscale_image(image: ImageFieldFile, max_width: int, max_height: int, save: bool = False) -> None:
    if image and image.width > max_width and image.height > max_height:
        buf = BytesIO()

        with resize_image(image, max_width, max_height=max_height) as im:
            im.save(buf, format=im.format)

        assert image.name
        image.save(name=image.name, content=ImageFile(file=buf), save=save)


def generate_thumbnail(
    from_field: ImageFieldFile,
    to_field: ImageFieldFile,
    size: int,
    save: bool = False,
) -> str | None:
    assert from_field.name
    stem, suffix = os.path.splitext(os.path.basename(from_field.name))
    thumbnail_filename = f"{stem}-thumbnail{suffix}"
    buf = BytesIO()

    with resize_image(from_field, size) as im:
        im.save(buf, format=im.format)
        mimetype = im.get_format_mimetype()

    to_field.save(name=thumbnail_filename, content=ImageFile(file=buf), save=save)
    return mimetype


@contextmanager
def resize_image(image, max_width: int, max_height: int | None = None) -> Generator[PILImageFile]:
    if max_height is None:
        max_height = max_width
    with Image.open(image) as im:
        ImageOps.exif_transpose(im, in_place=True)
        ratio = max(max_width / im.width, max_height / im.height)
        im.thumbnail((int(im.width * ratio), int(im.height * ratio)))
        yield im


def strip_markdown_images(md: str | None) -> str:
    # Basic stripping of Markdown image tags:
    if md:
        return re.sub(r"[\r\n]*!\[.*?\]\(.*?\)", "", md).strip()
    return ""
