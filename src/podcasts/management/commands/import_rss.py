import logging

import feedparser
from django.core.management import BaseCommand

from podcasts.models import Episode, Podcast


logging.getLogger("podcasts").setLevel(logging.INFO)


def bool_input(prompt: str, default: bool = True) -> bool:
    alternatives = "[Y/n]" if default else "[y/N]"
    reply = input(f"{prompt} {alternatives} ")
    if default:
        return reply.lower() != "n"
    return reply.lower() == "y"


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("url")
        parser.add_argument("slug")
        parser.add_argument("--update", "-u", action="store_true")
        parser.add_argument("--interactive", "-i", action="store_true")

    def handle(self, *args, **options):
        update = options["update"]
        slug = options["slug"]
        interactive = options["interactive"]

        podcast = Podcast.objects.filter(slug=slug).first()

        if interactive:
            if podcast:
                update = bool_input(f"Podcast {slug} already exists. Update?")
            elif not bool_input(f"Podcast {slug} does not exist. Create it?"):
                self.stdout.write("Nothing more to do, then.")
                return

        d = feedparser.parse(options["url"])

        if not (podcast and not update):
            if not podcast:
                if not interactive:
                    self.stdout.write(f"Podcast {slug} does not exist - creating")
                podcast = Podcast(slug=slug)
            elif update and not interactive:
                self.stdout.write(f"Podcast {slug} already exists - updating")
            podcast.update_from_feed(d.feed)
        elif not interactive:
            self.stdout.write(f"Podcast {slug} already exists - not updating")

        entries = d.get("entries", [])
        self.stdout.write(f"{len(entries)} entries (episodes) found in feed.")

        for entry in entries:
            episode: Episode | None = None

            try:
                number = int(entry.itunes_episode)
            except Exception:
                number = None
            try:
                season = int(entry.itunes_season)
            except Exception:
                season = None

            if number is not None:
                episode = Episode.objects.filter(podcast=podcast, number=number, season=season).first()
            else:
                episode = Episode.objects.filter(podcast=podcast, name=entry.title).first()

            self.stdout.write(f"season = {season}")
            if interactive:
                if episode:
                    update = bool_input(f"Episode '{episode}' already exists. Update it?")
                elif not bool_input(f"Episode '{entry.title}' does not exist. Create it?"):
                    continue

            if episode and not update:
                if not interactive:
                    self.stdout.write(f"Episode '{episode}' already exists - not updating")
                continue

            if not episode:
                if not interactive:
                    self.stdout.write(f"Episode '{entry.title}' does not exist - creating")
                episode = Episode(podcast=podcast)
            elif not interactive:
                self.stdout.write(f"Episode '{entry.title}' already exists - updating")

            episode.update_from_feed(entry)
