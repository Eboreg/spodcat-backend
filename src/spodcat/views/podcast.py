import itertools
import logging
from datetime import datetime
from typing import cast

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max, Prefetch
from django.http import Http404, HttpResponse
from django.template.loader import get_template
from django.template.response import TemplateResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from feedgen.entry import FeedEntry
from feedgen.ext.podcast import PodcastExtension
from feedgen.ext.podcast_entry import PodcastEntryExtension
from feedgen.feed import FeedGenerator
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_json_api import views

from spodcat import serializers
from spodcat.models import Episode, Podcast, PodcastContent
from spodcat.models.querysets import PodcastContentQuerySet
from spodcat.podcasting2 import Podcast2EntryExtension, Podcast2Extension
from spodcat.utils import markdown_to_html, strip_markdown_images
from spodcat.views.mixins import LogRequestMixin, PreloadIncludesMixin


logger = logging.getLogger(__name__)


class PodcastFeedGenerator(FeedGenerator):
    podcast: PodcastExtension
    podcast2: Podcast2Extension


class PodcastFeedEntry(FeedEntry):
    podcast: PodcastEntryExtension
    podcast2: Podcast2EntryExtension


class PodcastRssData:
    podcast: Podcast
    episodes: PodcastContentQuerySet[Episode]
    last_published: datetime | None
    authors: list[dict]
    author_string: str

    def __init__(self, pk: str):
        self.podcast = Podcast.objects.prefetch_related("authors", "categories").select_related("owner").get(slug=pk)
        self.authors = [{"name": a.get_full_name(), "email": a.email} for a in self.podcast.authors.all()]
        self.author_string = ", ".join([a["name"] for a in self.authors if a["name"]])
        self.episodes = (
            Episode.objects
            .filter(podcast=self.podcast)
            .select_related("podcast", "season")
            .listed()
            .with_has_chapters()
        )
        self.last_published = self.episodes.aggregate(last_published=Max("published"))["last_published"]

    # pylint: disable=no-member
    def get_rss_string(self):
        categories = [c.to_dict() for c in self.podcast.categories.all()]

        fg = FeedGenerator()
        fg.load_extension("podcast")
        fg.register_extension("podcast2", Podcast2Extension, Podcast2EntryExtension)
        fg = cast(PodcastFeedGenerator, fg)
        fg.title(self.podcast.name)
        fg.link([
            {"href": self.podcast.rss_url, "rel": "self", "type": "application/rss+xml"},
            {"href": self.podcast.frontend_url, "rel": "alternate"},
        ])
        fg.description(self.podcast.tagline or self.podcast.name)
        fg.podcast.itunes_type(self.podcast.itunes_type)

        if self.last_published:
            fg.lastBuildDate(self.last_published)
        if self.podcast.cover:
            fg.podcast.itunes_image(self.podcast.cover.url)
            if self.podcast.cover_height and self.podcast.cover_width:
                fg.image(
                    url=self.podcast.cover.url,
                    width=str(self.podcast.cover_width),
                    height=str(self.podcast.cover_height),
                )
            if self.podcast.cover_width:
                fg.podcast2.podcast_image(self.podcast.cover.url, self.podcast.cover_width)
        if self.podcast.cover_thumbnail and self.podcast.cover_thumbnail_width:
            fg.podcast2.podcast_image(self.podcast.cover_thumbnail.url, self.podcast.cover_thumbnail_width)
        if self.podcast.owner.email and self.podcast.owner.get_full_name():
            fg.podcast.itunes_owner(name=self.podcast.owner.get_full_name(), email=self.podcast.owner.email)
        if self.authors:
            fg.author(self.authors)
        if self.author_string:
            fg.podcast.itunes_author(self.author_string)
        if self.podcast.language:
            fg.language(self.podcast.language)
        if categories:
            fg.podcast.itunes_category(categories)
        fg.podcast2.podcast_guid(str(self.podcast.guid))

        for episode in self.episodes:
            description_html = episode.description_html + markdown_to_html(self.podcast.episode_rss_suffix)
            description_text = strip_markdown_images(episode.description)
            episode_rss_suffix_text = strip_markdown_images(self.podcast.episode_rss_suffix)
            if episode_rss_suffix_text:
                if description_text:
                    description_text += "\n\n"
                description_text += episode_rss_suffix_text

            fe = cast(PodcastFeedEntry, fg.add_entry(order="append"))
            if episode.has_chapters: # type: ignore
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
            if self.authors:
                fe.author(self.authors)
            if self.author_string:
                fe.podcast.itunes_author(self.author_string)

        return fg.rss_str(pretty=True)

    def get_template_context(self):
        return {
            "podcast": self.podcast,
            "last_published": self.last_published,
            "authors": self.authors,
            "author_string": self.author_string,
            "categories": itertools.groupby(self.podcast.categories.all(), lambda c: c.cat),
            "episodes": self.episodes,
        }


class PodcastViewSet(LogRequestMixin, PreloadIncludesMixin, views.ReadOnlyModelViewSet[Podcast]):
    prefetch_for_includes = {
        "__all__": [
            "links",
            "categories",
            Prefetch("contents", queryset=PodcastContent.objects.partial().listed().with_has_songs()),
        ]
    }
    select_for_includes = {
        "__all__": ["name_font_face"],
    }
    serializer_class = serializers.PodcastSerializer
    queryset = Podcast.objects.order_by_last_content(reverse=True)

    @extend_schema(responses={(200, "text/plain"): OpenApiTypes.NONE})
    @action(methods=["post"], detail=True)
    def ping(self, request: Request, pk: str):
        instance = self.get_object()

        if apps.is_installed("spodcat.logs"):
            from spodcat.logs.models import PodcastRequestLog
            self.log_request(request, PodcastRequestLog, podcast=instance)

        return Response()

    @extend_schema(responses={(200, "application/xml"): OpenApiTypes.STR})
    @action(methods=["get"], detail=True)
    def rss(self, request: Request, pk: str):
        # Both template and feedgen methods are available; going with feedgen
        # for now since it's considerably faster in tests.
        try:
            data = PodcastRssData(pk)
        except ObjectDoesNotExist as e:
            raise Http404 from e

        if apps.is_installed("spodcat.logs"):
            from spodcat.logs.models import PodcastRssRequestLog
            self.log_request(request, PodcastRssRequestLog, podcast=data.podcast)

        return self.__rss_feedgen(request=request, data=data)

    def __rss_feedgen(self, request: Request, data: PodcastRssData):
        rss = data.get_rss_string()

        if request.query_params.get("html"):
            return TemplateResponse(
                request=request._request, # pylint: disable=protected-access
                template="spodcat/rss.html",
                context={"rss": rss.decode() if isinstance(rss, bytes) else rss},
            )

        return HttpResponse(
            content=rss,
            content_type="application/xml; charset=utf-8",
            headers={
                "Content-Disposition": f"inline; filename=\"{data.podcast.slug}.rss.xml\"",
                "Access-Control-Allow-Origin": "*",
            },
        )

    # pylint: disable=unused-private-member
    def __rss_template(self, request: Request, data: PodcastRssData):
        context = data.get_template_context()

        if request.query_params.get("html"):
            return TemplateResponse(
                request=request._request, # pylint: disable=protected-access
                template="spodcat/rss.html",
                context={"rss": get_template("spodcat/rss.xml").render(context=context)},
            )

        return TemplateResponse(
            request=request._request, # pylint: disable=protected-access
            template="spodcat/rss.xml",
            context=context,
            content_type="application/xml; charset=utf-8",
            headers={
                "Content-Disposition": f"inline; filename=\"{data.podcast.slug}.rss.xml\"",
                "Access-Control-Allow-Origin": "*",
            },
        )
