import itertools
from datetime import datetime
from io import StringIO
from typing import TypedDict, cast

from django.db.models import Max
from feedgen.entry import FeedEntry
from feedgen.ext.podcast import PodcastExtension
from feedgen.ext.podcast_entry import PodcastEntryExtension
from feedgen.feed import FeedGenerator

from spodcat.models import Episode, Podcast
from spodcat.models.functions import rss_xml_storage
from spodcat.models.querysets import PodcastContentQuerySet
from spodcat.podcasting2 import Podcast2EntryExtension, Podcast2Extension
from spodcat.settings import spodcat_settings
from spodcat.utils import markdown_to_html, strip_markdown_images


class AuthorsDict(TypedDict):
    name: str
    email: str


class PodcastFeedGenerator(FeedGenerator):
    podcast: PodcastExtension
    podcast2: Podcast2Extension


class PodcastFeedEntry(FeedEntry):
    podcast: PodcastEntryExtension
    podcast2: Podcast2EntryExtension


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

    __authors: list[AuthorsDict] | None = None
    __episodes: PodcastContentQuerySet[Episode] | None = None
    __last_published: datetime | None = None
    __podcast: Podcast | None = None

    podcast_slug: str

    def __init__(self, pk: str):
        self.podcast_slug = pk

    def fetch_static_or_generate(self) -> str | bytes:
        if spodcat_settings.STATIC_RSS_XML:
            storage = rss_xml_storage()
            path = f"rss/{self.podcast_slug}.rss.xml"

            if storage.exists(path):
                with storage.open(path, "rt") as f:
                    return f.read()

        rss = self.generate()

        if spodcat_settings.STATIC_RSS_XML:
            self.save_static(rss)

        return rss

    def generate(self) -> str | bytes:
        podcast = self.get_podcast()
        authors = self.get_authors()
        author_string = self.get_author_string()
        categories = [c.to_dict() for c in podcast.categories.all()]

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

        if last_published := self.get_last_published():
            fg.lastBuildDate(last_published)

        if podcast.cover:
            fg.podcast.itunes_image(podcast.cover.url)

            if podcast.cover_height and podcast.cover_width:
                fg.image(
                    url=podcast.cover.url,
                    width=str(podcast.cover_width),
                    height=str(podcast.cover_height),
                )

            if podcast.cover_width:
                fg.podcast2.podcast_image(podcast.cover.url, podcast.cover_width)

        if podcast.cover_thumbnail and podcast.cover_thumbnail_width:
            fg.podcast2.podcast_image(podcast.cover_thumbnail.url, podcast.cover_thumbnail_width)

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

        for episode in self.get_episodes():
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

            if episode.image:
                fe.podcast.itunes_image(episode.image.url)

                if episode.image_width:
                    fe.podcast2.podcast_image(episode.image.url, episode.image_width)

            elif episode.season and episode.season.image:
                fe.podcast.itunes_image(episode.season.image.url)
                if episode.season.image_width:
                    fe.podcast2.podcast_image(episode.season.image.url, episode.season.image_width)

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

    def get_author_string(self):
        return ", ".join([a["name"] for a in self.get_authors() if a["name"]])

    def get_authors(self):
        if self.__authors is None:
            self.__authors = [{"name": a.get_full_name(), "email": a.email} for a in self.get_podcast().authors.all()]

        return self.__authors

    def get_episodes(self):
        if self.__episodes is None:
            self.__episodes = (
                Episode.objects.filter(podcast_id=self.podcast_slug)
                .select_related("podcast", "season")
                .published()
                .with_has_chapters()
            )

        return self.__episodes

    def get_last_published(self):
        if self.__last_published is None and self.__episodes is None:
            self.__last_published = self.get_episodes().aggregate(last_published=Max("published"))["last_published"]

        return self.__last_published

    def get_podcast(self):
        if self.__podcast is None:
            self.__podcast = (
                Podcast.objects.prefetch_related("authors", "categories")
                .select_related("owner")
                .get(slug=self.podcast_slug)
            )

        return self.__podcast

    def get_template_context(self):
        podcast = self.get_podcast()

        return {
            "podcast": podcast,
            "last_published": self.get_last_published(),
            "authors": self.get_authors(),
            "author_string": self.get_author_string(),
            "categories": itertools.groupby(podcast.categories.all(), lambda c: c.cat),
            "episodes": self.get_episodes(),
        }

    def regenerate_static(self):
        self.save_static(self.generate())

    def save_static(self, rss: str | bytes):
        rss = rss.decode() if isinstance(rss, bytes) else rss
        storage = rss_xml_storage()
        filename = f"rss/{self.podcast_slug}.rss.xml"

        if storage.exists(filename):
            storage.delete(filename)

        rss_buffer = StringIO(rss)
        storage.save(filename, rss_buffer)
