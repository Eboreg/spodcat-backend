import math
from io import BytesIO
from typing import TYPE_CHECKING, BinaryIO, Generator, Literal

import feedparser
from django.core.files.images import ImageFile
from django.db.models.fields.files import FieldFile, ImageFieldFile
from PIL import Image
from pydub import AudioSegment


if TYPE_CHECKING:
    from podcasts.models import Podcast
    from users.models import User


def get_audio_file_dbfs_array(file: BinaryIO, format_name: str) -> list[float]:
    dbfs_values = [-100.0 if s.dBFS < -100 else s.dBFS for s in split_audio_file(file, 200, format_name)]
    min_dbfs = min(dbfs_values)
    dbfs_values = [dbfs - min_dbfs for dbfs in dbfs_values]
    max_dbfs = max(dbfs_values)
    multiplier = 100 / max_dbfs

    return [dbfs * multiplier for dbfs in dbfs_values]


def split_audio_file(file: BinaryIO, parts: int, format_name: str) -> Generator[AudioSegment, None, None]:
    whole = AudioSegment.from_file(file, format_name)
    i = 0
    n = math.ceil(len(whole) / parts)

    while i < len(whole):
        yield whole[i:i + n]
        i += n


def read_rss_from_url(
    url: str,
    podcast: "Podcast | None" = None,
    owner: "User | None" = None,
    on_conflict: Literal["ignore", "update"] = "ignore",
):
    from podcasts.models import Episode, Podcast

    d = feedparser.parse(url)
    podcast = Podcast.from_feed(d.feed, podcast=podcast)
    if owner:
        podcast.owners.add(owner)
    for entry in d.get("entries", []):
        Episode.from_feed(entry=entry, podcast=podcast, on_conflict=on_conflict)
    return podcast


def downscale_image(image: ImageFieldFile, max_width: int, max_height: int, save: bool = False):
    if image and image.width > max_width and image.height > max_height:
        buf = BytesIO()

        with Image.open(image) as im:
            ratio = max(max_width / im.width, max_height / im.height)
            im.thumbnail((int(im.width * ratio), int(im.height * ratio)))
            im.save(buf, format=im.format)

        image.save(name=image.name, content=ImageFile(file=buf), save=save)


def delete_storage_file(file: FieldFile):
    if file:
        file.storage.delete(name=file.name)
