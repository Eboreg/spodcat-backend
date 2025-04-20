from typing import cast
from urllib.parse import urljoin

from django.conf import settings
from django.db.models import Max, Prefetch
from django.http import HttpResponse
from feedgen.entry import FeedEntry
from feedgen.ext.podcast import PodcastExtension
from feedgen.ext.podcast_entry import PodcastEntryExtension
from feedgen.feed import FeedGenerator
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_json_api import views

from logs.models import PodcastRequestLog, PodcastRssRequestLog
from podcasts import serializers
from podcasts.models import Episode, Podcast, PodcastContent


class PodcastFeedGenerator(FeedGenerator):
    podcast: PodcastExtension


class PodcastFeedEntry(FeedEntry):
    podcast: PodcastEntryExtension


class PodcastViewSet(views.ReadOnlyModelViewSet):
    prefetch_for_includes = {
        "authors": ["authors"],
        "categories": ["categories"],
        "contents": [
            Prefetch("contents", queryset=PodcastContent.objects.partial().visible().with_has_songs()),
        ],
        "links": ["links"],
    }
    queryset = Podcast.objects.all()
    serializer_class = serializers.PodcastSerializer

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
        episode_qs = Episode.objects.filter(podcast=podcast).visible()
        last_published = episode_qs.aggregate(last_published=Max("published"))["last_published"]
        author_string = ", ".join([a["name"] for a in authors if a["name"]])

        rss_request_log = PodcastRssRequestLog.create(request=request, podcast=podcast)

        fg = FeedGenerator()
        fg.load_extension("podcast")
        fg = cast(PodcastFeedGenerator, fg)
        fg.title(podcast.name)
        fg.link(href=urljoin(settings.FRONTEND_ROOT_URL, pk))
        fg.description(podcast.tagline or podcast.name)
        fg.podcast.itunes_type("episodic")
        if last_published:
            fg.lastBuildDate(last_published)
        if podcast.cover:
            fg.image(podcast.cover.url)
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

        for episode in episode_qs:
            fe = cast(PodcastFeedEntry, fg.add_entry(order="append"))
            fe.title(episode.name)
            fe.content(episode.description_html, type="CDATA")
            fe.description(episode.description_text)
            fe.podcast.itunes_summary(episode.description_text)
            fe.published(episode.published)
            fe.podcast.itunes_season(episode.season)
            fe.podcast.itunes_episode(episode.number)
            fe.podcast.itunes_episode_type("full")
            fe.link(href=urljoin(settings.FRONTEND_ROOT_URL, f"{podcast.slug}/episode/{episode.slug}"))
            fe.podcast.itunes_duration(round(episode.duration_seconds))
            if episode.image:
                fe.podcast.itunes_image(episode.image.url)
            if episode.audio_file:
                fe.enclosure(
                    url=f"{episode.audio_file.url}?_rsslog={rss_request_log.pk}",
                    type=episode.audio_content_type,
                    length=episode.audio_file_length,
                )
            fe.guid(guid=str(episode.id), permalink=False)
            if authors:
                fe.author(authors)
            if author_string:
                fe.podcast.itunes_author(author_string)

        return HttpResponse(content=fg.rss_str(pretty=True), content_type="application/xml; charset=utf-8")
