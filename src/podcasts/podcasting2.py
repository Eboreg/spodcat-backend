from feedgen.ext.base import BaseEntryExtension, BaseExtension
from feedgen.util import xml_elem


NAMESPACE = "https://podcastindex.org/namespace/1.0"


class Podcast2Extension(BaseExtension):
    def __init__(self):
        self.__podcast_guid = None

    def extend_ns(self):
        return {"podcast": NAMESPACE}

    def extend_rss(self, feed):
        channel = feed[0]

        if self.__podcast_guid is not None:
            guid = xml_elem("{%s}guid" % NAMESPACE, channel)
            guid.text = self.__podcast_guid

        return feed

    def podcast_guid(self, guid: str | None = None):
        if guid is not None:
            self.__podcast_guid = guid
        return self.__podcast_guid


class Podcast2EntryExtension(BaseEntryExtension):
    def __init__(self):
        self.__podcast_chapters = None
        self.__podcast_season = None
        self.__podcast_season_name = None
        self.__podcast_episode = None
        self.__podcast_episode_display = None

    def extend_rss(self, feed):
        if self.__podcast_chapters:
            chapters = xml_elem("{%s}chapters" % NAMESPACE, feed)
            chapters.attrib["url"] = self.__podcast_chapters
            chapters.attrib["type"] = "application/json+chapters"

        if self.__podcast_season is not None:
            season = xml_elem("{%s}season" % NAMESPACE, feed)
            season.text = str(self.__podcast_season)
            if self.__podcast_season_name:
                season.attrib["name"] = self.__podcast_season_name

        if self.__podcast_episode is not None:
            episode = xml_elem("{%s}episode" % NAMESPACE, feed)
            episode.text = str(self.__podcast_episode)
            if self.__podcast_episode_display:
                episode.attrib["display"] = self.__podcast_episode_display

        return feed

    def podcast_chapters(self, url: str | None = None):
        if url is not None:
            self.__podcast_chapters = url
        return self.__podcast_chapters

    def podcast_season(self, season: int | None = None, name: str | None = None):
        if season is not None:
            self.__podcast_season = season
            self.__podcast_season_name = name
        return self.__podcast_season, self.__podcast_season_name

    def podcast_episode(self, episode: int | float | None = None, display: str | None = None):
        if episode is not None:
            self.__podcast_episode = episode
            self.__podcast_episode_display = display
        return self.__podcast_episode, self.__podcast_episode_display
