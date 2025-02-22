from typing import cast
from urllib.parse import urljoin

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from feedgen.entry import FeedEntry
from feedgen.ext.podcast import PodcastExtension
from feedgen.ext.podcast_entry import PodcastEntryExtension
from feedgen.feed import FeedGenerator
from rest_framework_json_api import views

from podcasts import serializers
from podcasts.models import Episode, Podcast


class PodcastFeedGenerator(FeedGenerator):
    podcast: PodcastExtension


class PodcastFeedEntry(FeedEntry):
    podcast: PodcastEntryExtension


class PodcastViewSet(views.ReadOnlyModelViewSet):
    queryset = Podcast.objects.all()
    serializer_class = serializers.PodcastSerializer
    prefetch_for_includes = {
        "episodes": ["episodes"],
        "owners": ["owners"],
        "categories": ["categories"],
        "links": ["links"],
    }


class EpisodeViewSet(views.ReadOnlyModelViewSet):
    queryset = Episode.objects.all()
    serializer_class = serializers.EpisodeSerializer
    select_for_includes = {
        "podcast": ["podcast"],
    }


# pylint: disable=no-member
def podcast_rss(request: HttpRequest, slug: str):
    podcast = Podcast.objects.prefetch_related("episodes", "owners", "categories").get(slug=slug)
    authors = ", ".join(o.get_full_name() for o in podcast.owners.all())
    categories = [c.to_dict() for c in podcast.categories.all()]

    fg = FeedGenerator()
    fg.load_extension("podcast")
    fg = cast(PodcastFeedGenerator, fg)
    fg.title(podcast.name)
    fg.link(href=urljoin(settings.FRONTEND_ROOT_URL, slug))
    if podcast.description:
        fg.description(podcast.description)
        fg.podcast.itunes_summary(podcast.description)
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

    for episode in podcast.episodes.all():
        if not episode.is_published():
            continue
        fe = cast(PodcastFeedEntry, fg.add_entry(order="append"))
        fe.title(episode.name)
        fe.description(episode.description)
        fe.published(episode.published)
        fe.podcast.itunes_episode(episode.episode)
        fe.link(href=episode.frontend_url)
        fe.podcast.itunes_duration(round(episode.duration_seconds))
        fe.enclosure(
            url=episode.audio_file.url,
            type=episode.audio_content_type,
            length=episode.audio_file_length,
        )
        fe.guid(guid=f"{podcast.slug}-{episode.slug}", permalink=False)

    # return HttpResponse(content=fg.rss_str(pretty=True), content_type="application/rss+xml; charset=utf-8")
    return HttpResponse(content=fg.rss_str(pretty=True), content_type="application/xml; charset=utf-8")
