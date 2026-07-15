from django.contrib import admin

from spodcat.models import Artist, Comment, Episode, EpisodeSong, FontFace, Podcast, Post, Season

from .artist import ArtistAdmin
from .comment import CommentAdmin
from .episode import EpisodeAdmin
from .episode_song import EpisodeSongAdmin
from .font_face import FontFaceAdmin
from .podcast import PodcastAdmin
from .post import PostAdmin
from .season import SeasonAdmin


admin.site.register(Artist, ArtistAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(EpisodeSong, EpisodeSongAdmin)
admin.site.register(Episode, EpisodeAdmin)
admin.site.register(FontFace, FontFaceAdmin)
admin.site.register(Podcast, PodcastAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(Season, SeasonAdmin)
