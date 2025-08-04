import itertools
import logging
from datetime import datetime
from typing import cast

from django.apps import apps
from django.db.models import Max, Prefetch
from django.http import HttpResponse
from django.template.loader import get_template
from django.template.response import TemplateResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from feedgen.entry import FeedEntry
from feedgen.ext.podcast import PodcastExtension
from feedgen.ext.podcast_entry import PodcastEntryExtension
from feedgen.feed import FeedGenerator
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_json_api import views

from spodcat import serializers
from spodcat.models import Episode, Podcast, PodcastContent
from spodcat.models.querysets import PodcastContentQuerySet
from spodcat.podcasting2 import Podcast2EntryExtension, Podcast2Extension
from spodcat.views.mixins import LogRequestMixin


logger = logging.getLogger(__name__)


class PodcastFeedGenerator(FeedGenerator):
    podcast: PodcastExtension
    podcast2: Podcast2Extension


class PodcastFeedEntry(FeedEntry):
    podcast: PodcastEntryExtension
    podcast2: Podcast2EntryExtension


class PodcastViewSet(LogRequestMixin, views.ReadOnlyModelViewSet[Podcast]):
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
        queryset = Podcast.objects.prefetch_related("authors", "categories").select_related("owner")
        podcast: Podcast = get_object_or_404(queryset, slug=pk)
        authors = [{"name": o.get_full_name(), "email": o.email} for o in podcast.authors.all()]
        episode_qs = (
            Episode.objects
            .filter(podcast=podcast)
            .select_related("podcast", "season2")
            .listed()
            .with_has_chapters()
        )

        if apps.is_installed("spodcat.logs"):
            from spodcat.logs.models import PodcastRssRequestLog
            self.log_request(request, PodcastRssRequestLog, podcast=podcast)

        return self.rss_feedgen(
            request=request,
            podcast=podcast,
            episode_qs=episode_qs,
            last_published=episode_qs.aggregate(last_published=Max("published"))["last_published"],
            author_string=", ".join([a["name"] for a in authors if a["name"]]),
            authors=authors,
        )

    # pylint: disable=no-member
    def rss_feedgen(
        self,
        request: Request,
        podcast: Podcast,
        episode_qs: PodcastContentQuerySet[Episode],
        last_published: datetime | None,
        authors: list[dict],
        author_string: str,
    ):
        categories = [c.to_dict() for c in podcast.categories.all()]

        fg = FeedGenerator()
        fg.load_extension("podcast")
        fg.register_extension("podcast2", Podcast2Extension, Podcast2EntryExtension)
        fg = cast(PodcastFeedGenerator, fg)
        fg.title(podcast.name)
        fg.link([
            {"href": podcast.rss_url, "rel": "self", "type": "application/rss+xml"},
            {"href": podcast.frontend_url, "rel": "alternate"},
        ])
        fg.description(podcast.tagline or podcast.name)
        fg.podcast.itunes_type(podcast.itunes_type)
        if last_published:
            fg.lastBuildDate(last_published)
        if podcast.cover:
            fg.podcast.itunes_image(podcast.cover.url)
            if podcast.cover_height and podcast.cover_width:
                fg.image(url=podcast.cover.url, width=str(podcast.cover_width), height=str(podcast.cover_height))
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

        for episode in episode_qs:
            fe = cast(PodcastFeedEntry, fg.add_entry(order="append"))
            if episode.has_chapters: # type: ignore
                fe.podcast2.podcast_chapters(episode.chapters_url)
            fe.title(episode.name)
            fe.content(episode.description_html, type="CDATA")
            fe.description(episode.description_text)
            fe.podcast.itunes_summary(episode.description_text)
            fe.published(episode.published)
            if episode.season2:
                fe.podcast.itunes_season(episode.season2.number)
                fe.podcast.itunes_season(episode.season2.number)
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
            elif episode.season2 and episode.season2.image:
                fe.podcast.itunes_image(episode.season2.image.url)
                if episode.season2.image_width:
                    fe.podcast2.podcast_image(episode.season2.image.url, episode.season2.image_width)
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

        rss = fg.rss_str(pretty=True)

        if request.query_params.get("html"):
            return TemplateResponse(
                request=request._request, # pylint: disable=protected-access
                template="spodcat/rss.html",
                context={"rss": rss.decode()},
            )

        return HttpResponse(
            content=rss,
            content_type="application/xml; charset=utf-8",
            headers={
                "Content-Disposition": f"inline; filename=\"{podcast.slug}.rss.xml\"",
                "Access-Control-Allow-Origin": "*",
            },
        )

    def rss_template(
        self,
        request: Request,
        podcast: Podcast,
        episode_qs: PodcastContentQuerySet[Episode],
        last_published: datetime | None,
        authors: list[dict],
        author_string: str,
    ):
        context = {
            "podcast": podcast,
            "last_published": last_published,
            "authors": authors,
            "author_string": author_string,
            "categories": itertools.groupby(podcast.categories.all(), lambda c: c.cat),
            "episodes": episode_qs,
        }

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
                "Content-Disposition": f"inline; filename=\"{podcast.slug}.rss.xml\"",
                "Access-Control-Allow-Origin": "*",
            },
        )
