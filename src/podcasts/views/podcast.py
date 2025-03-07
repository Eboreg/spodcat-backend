from typing import cast
from urllib.parse import urljoin

from django.conf import settings
from django.db.models import Prefetch
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
from podcasts.models import Podcast, PodcastContent


class PodcastFeedGenerator(FeedGenerator):
    podcast: PodcastExtension


class PodcastFeedEntry(FeedEntry):
    podcast: PodcastEntryExtension


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
                )
            )
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
        is_singleton: bool = self.get_queryset().count() == 1
        podcast: Podcast = self.get_queryset().prefetch_related("owners", "categories").get(slug=pk)
        authors = ", ".join(o.get_full_name() for o in podcast.owners.all())
        categories = [c.to_dict() for c in podcast.categories.all()]

        PodcastRssRequestLog.create(request=request, podcast=podcast)

        fg = FeedGenerator()
        fg.load_extension("podcast")
        fg = cast(PodcastFeedGenerator, fg)
        fg.title(podcast.name)

        if is_singleton:
            fg.link(href=settings.FRONTEND_ROOT_URL)
        else:
            fg.link(href=urljoin(settings.FRONTEND_ROOT_URL, pk))

        if podcast.tagline:
            description = "<![CDATA[" + podcast.tagline + "]]>"
            fg.description(description)
            fg.podcast.itunes_summary(description)
        if podcast.cover:
            fg.image(podcast.cover.url)
            fg.podcast.itunes_image(podcast.cover.url)

        for owner in podcast.owners.all():
            if owner.get_full_name() and owner.email:
                fg.podcast.itunes_owner(name=owner.get_full_name(), email=owner.email)
                break

        if authors:
            fg.podcast.itunes_author(authors)
        if podcast.language:
            fg.language(podcast.language)
        if categories:
            fg.podcast.itunes_category(categories)

        for episode in podcast.published_episodes:
            if not episode.is_published():
                continue
            fe = cast(PodcastFeedEntry, fg.add_entry(order="append"))
            fe.title(episode.name)
            fe.description("<![CDATA[" + episode.description_html + "]]>")
            fe.published(episode.published)
            fe.podcast.itunes_episode(episode.number)
            if is_singleton:
                fe.link(href=urljoin(settings.FRONTEND_ROOT_URL, f"episode/{episode.slug}"))
            else:
                fe.link(href=urljoin(settings.FRONTEND_ROOT_URL, f"{podcast.slug}/episode/{episode.slug}"))
            fe.podcast.itunes_duration(round(episode.duration_seconds))
            fe.enclosure(
                url=episode.audio_url,
                type=episode.audio_content_type,
                length=episode.audio_file_length,
            )
            fe.guid(guid=f"{podcast.slug}-{episode.slug}", permalink=False)

        return HttpResponse(content=fg.rss_str(pretty=True), content_type="application/xml; charset=utf-8")
