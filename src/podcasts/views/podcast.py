from typing import cast
from urllib.parse import urljoin

from django.conf import settings
from django.db.models import Max, Prefetch
from django.http import HttpResponse
from django.utils import timezone
from feedgen.entry import FeedEntry
from feedgen.ext.base import BaseEntryExtension
from feedgen.ext.podcast import PodcastExtension
from feedgen.ext.podcast_entry import PodcastEntryExtension
from feedgen.feed import FeedGenerator
from feedgen.util import xml_elem
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_json_api import views

from logs.models import PodcastRequestLog, PodcastRssRequestLog
from podcasts import serializers
from podcasts.models import Podcast, PodcastContent
from podcasts.models.episode import Episode


class ContentEncodedExtension(BaseEntryExtension):
    def __init__(self):
        self.__content_encoded = None

    def extend_ns(self):
        return {"content": "http://purl.org/rss/1.0/modules/content/"}

    def extend_rss(self, feed):
        namespace = "http://purl.org/rss/1.0/modules/content/"

        if self.__content_encoded:
            content_encoded = xml_elem("{%s}encoded" % namespace, feed)
            content_encoded.text = self.__content_encoded

        return feed

    def content_encoded(self, content_encoded=None):
        if content_encoded is not None:
            self.__content_encoded = f"<![CDATA[{content_encoded}]]>"
        return self.__content_encoded


class PodcastFeedGenerator(FeedGenerator):
    podcast: PodcastExtension


class PodcastFeedEntry(FeedEntry):
    podcast: PodcastEntryExtension
    content_encoded: ContentEncodedExtension


class PodcastViewSet(views.ReadOnlyModelViewSet):
    queryset = Podcast.objects.all()
    serializer_class = serializers.PodcastSerializer
    prefetch_for_includes = {
        "categories": ["categories"],
        "contents": [
            Prefetch("contents", queryset=PodcastContent.objects.partial().visible().prefetch_related("songs")),
        ],
        "links": ["links"],
        "authors": ["authors"],
    }

    @action(methods=["post"], detail=True)
    def ping(self, request: Request, pk: str):
        instance = self.get_object()
        PodcastRequestLog.create(request=request, podcast=instance)
        return Response()

    @action(methods=["get"], detail=True)
    # pylint: disable=no-member
    def rss(self, request: Request, pk: str):
        podcast: Podcast = (
            self.get_queryset()
            .prefetch_related("authors", "categories")
            .select_related("owner")
            .get(slug=pk)
        )
        authors = [{"name": o.get_full_name(), "email": o.email} for o in podcast.authors.all()]
        categories = [c.to_dict() for c in podcast.categories.all()]
        episode_qs = Episode.objects.filter(podcast=podcast, published__lte=timezone.now(), is_draft=False)
        last_published = episode_qs.aggregate(last_published=Max("published"))["last_published"]
        author_string = ", ".join([a["name"] for a in authors if a["name"]])

        PodcastRssRequestLog.create(request=request, podcast=podcast)

        fg = FeedGenerator()
        fg.load_extension("podcast")
        fg = cast(PodcastFeedGenerator, fg)
        fg.title(podcast.name)
        fg.link(href=urljoin(settings.FRONTEND_ROOT_URL, pk))
        fg.description(f"<![CDATA[{podcast.tagline or podcast.name}]]>")
        fg.podcast.itunes_type("episodic")
        if last_published:
            fg.lastBuildDate(last_published)
        if podcast.cover:
            fg.image(podcast.cover.url)
        if podcast.owner and podcast.owner.email and podcast.owner.get_full_name():
            fg.podcast.itunes_owner(name=podcast.owner.get_full_name(), email=podcast.owner.email)
        if authors:
            fg.author(authors)
        if author_string:
            fg.podcast.itunes_author(author_string)
        if podcast.language:
            fg.language(podcast.language)
        if categories:
            fg.podcast.itunes_category(categories)

        for episode in episode_qs:
            fe = cast(PodcastFeedEntry, fg.add_entry(order="append"))
            fe.register_extension("content_encoded", ContentEncodedExtension)
            fe.title(episode.name)
            fe.description(f"<![CDATA[{episode.description_html}]]>")
            fe.published(episode.published)
            fe.podcast.itunes_season(episode.season)
            fe.podcast.itunes_episode(episode.number)
            fe.podcast.itunes_episode_type("full")
            fe.link(href=urljoin(settings.FRONTEND_ROOT_URL, f"{podcast.slug}/episode/{episode.slug}"))
            fe.podcast.itunes_duration(round(episode.duration_seconds))
            fe.content_encoded.content_encoded(episode.description_html)
            if episode.image:
                fe.podcast.itunes_image(episode.image.url)
            fe.enclosure(
                url=episode.audio_url,
                type=episode.audio_content_type,
                length=episode.audio_file_length,
            )
            fe.guid(guid=str(episode.id), permalink=False)
            if authors:
                fe.author(authors)
            if author_string:
                fe.podcast.itunes_author(author_string)

        return HttpResponse(content=fg.rss_str(pretty=True), content_type="application/xml; charset=utf-8")
