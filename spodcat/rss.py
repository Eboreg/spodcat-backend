from __future__ import annotations

from abc import ABC, abstractmethod
from io import StringIO
from typing import TYPE_CHECKING, TypedDict, cast

from django.db.models import Max
from feedgen.entry import FeedEntry
from feedgen.feed import FeedGenerator

from spodcat.images import strip_markdown_images
from spodcat.models import Episode, Podcast
from spodcat.models.functions import rss_xml_storage
from spodcat.podcasting2 import Podcast2EntryExtension, Podcast2Extension
from spodcat.settings import spodcat_settings
from spodcat.utils import markdown_to_html


if TYPE_CHECKING:
    from collections.abc import Iterator

    from feedgen.ext.podcast import PodcastExtension
    from feedgen.ext.podcast_entry import PodcastEntryExtension


RSS_MEMORY_CACHE: dict[str, str | bytes] = {}


class AuthorsDict(TypedDict):
    name: str
    email: str


class PodcastFeedGenerator(FeedGenerator):
    podcast: PodcastExtension
    podcast2: Podcast2Extension


class PodcastFeedEntry(FeedEntry):
    podcast: PodcastEntryExtension
    podcast2: Podcast2EntryExtension


class AbstractPodcastRssCache(ABC):
    def __init__(self, podcast_slug: str):
        self.podcast_slug = podcast_slug

    @abstractmethod
    def fetch(self) -> str | bytes | None: ...

    @abstractmethod
    def save(self, rss: str | bytes): ...


class PodcastRssFileCache(AbstractPodcastRssCache):
    def __init__(self, podcast_slug: str):
        super().__init__(podcast_slug)
        self.storage = rss_xml_storage()
        self.path = f"rss/{self.podcast_slug}.rss.xml"

    def fetch(self) -> str | bytes | None:
        if self.storage.exists(self.path):
            with self.storage.open(self.path, "rt") as f:
                return f.read()

        return None

    def save(self, rss: str | bytes):
        rss = rss.decode() if isinstance(rss, bytes) else rss
        if self.storage.exists(self.path):
            self.storage.delete(self.path)
        rss_buffer = StringIO(rss)
        self.storage.save(self.path, rss_buffer)


class PodcastRssMemoryCache(AbstractPodcastRssCache):
    def fetch(self) -> str | bytes | None:
        if self.podcast_slug in RSS_MEMORY_CACHE:
            return RSS_MEMORY_CACHE[self.podcast_slug]
        return None

    def save(self, rss: str | bytes):
        RSS_MEMORY_CACHE[self.podcast_slug] = rss


class PodcastRssData:
    """
    Models whose creation/updates/deletion should result in static RSS
    regeneration:

        * Podcast
        * Episode
        * User (could be podcast author/owner)
        * Category
        * Season
        * EpisodeChapter
        * EpisodeSong
    """

    def __init__(self, podcast_slug: str):
        self.podcast_slug = podcast_slug

    def get(self) -> str | bytes:
        missing: list[AbstractPodcastRssCache] = []
        rss: str | bytes | None = None

        for cache in self.__get_caches():
            if rss := cache.fetch():
                break
            missing.append(cache)

        if rss is None:
            rss = self.__generate()

        for cache in missing:
            cache.save(rss)

        return rss

    def renew_cache(self):
        self.__save_to_cache(self.__generate())

    def __generate(self) -> str | bytes:
        podcast = (
            Podcast.objects.prefetch_related("authors", "categories")
            .select_related("owner")
            .get(slug=self.podcast_slug)
        )
        episodes = (
            Episode.objects.filter(podcast_id=self.podcast_slug)
            .select_related("season", "podcast")
            .published()
            .with_has_chapters()
        )
        authors = [{"name": a.get_full_name(), "email": a.email} for a in podcast.authors.all()]
        author_string = ", ".join([a["name"] for a in authors if a["name"]])
        categories = [c.to_dict() for c in podcast.categories.all()]
        last_published = episodes.aggregate(last_published=Max("published"))["last_published"]

        fg = FeedGenerator()
        fg.load_extension("podcast")
        fg.register_extension("podcast2", Podcast2Extension, Podcast2EntryExtension)
        fg = cast(PodcastFeedGenerator, fg)
        fg.title(podcast.name)
        fg.link(
            [
                {"href": podcast.rss_url, "rel": "self", "type": "application/rss+xml"},
                {"href": podcast.frontend_url, "rel": "alternate"},
            ]
        )
        fg.description(podcast.tagline or podcast.name)
        fg.podcast.itunes_type(podcast.itunes_type)

        if last_published:
            fg.lastBuildDate(last_published)

        fg.podcast2.podcast_image(podcast.cover_data, podcast.cover_thumbnail_data)
        fg.podcast2.podcast_image_deprecated(podcast.cover_data, podcast.cover_thumbnail_data)

        if podcast.cover:
            fg.podcast.itunes_image(podcast.cover.url)
            if podcast.cover_height and podcast.cover_width:
                fg.image(
                    url=podcast.cover.url,
                    width=str(podcast.cover_width),
                    height=str(podcast.cover_height),
                )

        if podcast.owner.email and podcast.owner.get_full_name():
            fg.podcast.itunes_owner(name=podcast.owner.get_full_name(), email=podcast.owner.email)

        if authors:
            fg.author(authors)

        if author_string:
            fg.podcast.itunes_author(author_string)

        if podcast.language:
            fg.language(podcast.language)

        if categories:
            fg.podcast.itunes_category(categories)

        fg.podcast2.podcast_guid(str(podcast.guid))
        fg.podcast2.podcast_block(*podcast.blocked_platforms)

        for episode in episodes:
            description_html = episode.description_html + markdown_to_html(podcast.episode_rss_suffix)
            description_text = strip_markdown_images(episode.description)
            episode_rss_suffix_text = strip_markdown_images(podcast.episode_rss_suffix)

            if episode_rss_suffix_text:
                if description_text:
                    description_text += "\n\n"
                description_text += episode_rss_suffix_text

            fe = cast(PodcastFeedEntry, fg.add_entry(order="append"))

            if episode.has_chapters:  # pyright: ignore[reportAttributeAccessIssue]
                fe.podcast2.podcast_chapters(episode.chapters_url)

            fe.title(episode.name)
            fe.content(description_html, type="CDATA")
            fe.description(description_text)
            fe.podcast.itunes_summary(description_text)
            fe.published(episode.published)

            if episode.season:
                fe.podcast.itunes_season(episode.season.number)
                fe.podcast.itunes_season(episode.season.number)

            if episode.whole_number is not None:
                fe.podcast.itunes_episode(episode.whole_number)

            fe.podcast2.podcast_episode(episode.number)
            fe.podcast.itunes_episode_type("full")
            fe.link(href=episode.frontend_url)
            fe.podcast.itunes_duration(round(episode.duration_seconds))

            if Episode.ImageUsage.RSS in episode.image_usage:
                if episode.image:
                    fe.podcast.itunes_image(episode.image.url)
                    fe.podcast2.podcast_image(episode.image_data, episode.image_thumbnail_data)
                    fe.podcast2.podcast_image_deprecated(episode.image_data, episode.image_thumbnail_data)

                elif episode.season and episode.season.image:
                    fe.podcast.itunes_image(episode.season.image.url)
                    fe.podcast2.podcast_image(episode.season.image_data, episode.season.image_thumbnail_data)
                    fe.podcast2.podcast_image_deprecated(episode.season.image_data, episode.season.image_thumbnail_data)

            audio_file_url = episode.get_audio_file_url()

            if audio_file_url:
                fe.enclosure(
                    url=audio_file_url,
                    type=episode.audio_content_type,
                    length=episode.audio_file_length,
                )

            fe.guid(guid=str(episode.id), permalink=False)

            if authors:
                fe.author(authors)

            if author_string:
                fe.podcast.itunes_author(author_string)

        return fg.rss_str(pretty=True)

    def __get_caches(self) -> Iterator[AbstractPodcastRssCache]:
        for method in spodcat_settings.CACHE_RSS_XML:
            if method == "memory":
                yield PodcastRssMemoryCache(self.podcast_slug)
            elif method == "file":
                yield PodcastRssFileCache(self.podcast_slug)

    def __save_to_cache(self, rss: str | bytes):
        for cache in self.__get_caches():
            cache.save(rss)
