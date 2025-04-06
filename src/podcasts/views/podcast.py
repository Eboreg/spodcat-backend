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
            Prefetch(
                "contents",
                queryset=PodcastContent.objects.only(
                    "Episode___audio_file",
                    "Episode___duration_seconds",
                    "Episode___number",
                    "Episode___podcastcontent_ptr_id",
                    "name",
                    "podcast",
                    "polymorphic_ctype_id",
                    "published",
                    "slug",
                ).filter(published__lte=timezone.now(), is_draft=False),
            ),
        ],
        "links": ["links"],
        "owners": ["owners"],
    }

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        PodcastRequestLog.create(request=request, podcast=instance)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(methods=["get"], detail=True)
    # pylint: disable=no-member
    def rss(self, request: Request, pk: str):
        podcast: Podcast = self.get_queryset().prefetch_related("owners", "categories").get(slug=pk)
        authors = [{"name": o.get_full_name(), "email": o.email} for o in podcast.owners.all()]
        categories = [c.to_dict() for c in podcast.categories.all()]
        episode_qs = Episode.objects.filter(podcast=podcast, published__lte=timezone.now(), is_draft=False)
        last_published = episode_qs.aggregate(last_published=Max("published"))["last_published"]

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

        for owner in podcast.owners.all():
            if owner.get_full_name() and owner.email:
                fg.podcast.itunes_owner(name=owner.get_full_name(), email=owner.email)
                break

        if authors:
            fg.author(authors)
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
            fe.podcast.itunes_episode(episode.number)
            fe.podcast.itunes_episode_type("full")
            fe.link(href=urljoin(settings.FRONTEND_ROOT_URL, f"{podcast.slug}/episode/{episode.slug}"))
            fe.podcast.itunes_duration(round(episode.duration_seconds))
            fe.content_encoded.content_encoded(episode.description_html)
            fe.enclosure(
                url=episode.audio_url,
                type=episode.audio_content_type,
                length=episode.audio_file_length,
            )
            fe.guid(guid=str(episode.id), permalink=False)

        return HttpResponse(content=fg.rss_str(pretty=True), content_type="application/xml; charset=utf-8")
