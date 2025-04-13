import tempfile
from functools import update_wrapper
from threading import Thread
from typing import BinaryIO

from django.contrib import admin
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import models
from django.db.models import Count, F, OuterRef, Q, Subquery
from django.forms import ModelForm
from django.http import HttpRequest, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from martor.models import MartorField
from pydub.utils import mediainfo

from logs.models import (
    AbstractRequestLog,
    PodcastContentAudioRequestLog,
    PodcastRequestLog,
    PodcastRssRequestLog,
)
from podcasts.fields import (
    AdminMartorWidget,
    ArtistAutocompleteWidget,
    ArtistMultipleChoiceField,
    EpisodeSongForm,
    seconds_to_timestamp,
)
from podcasts.models import (
    Artist,
    Comment,
    Episode,
    EpisodeSong,
    Podcast,
    PodcastLink,
    Post,
)
from podcasts.models.podcast_content import PodcastContent
from podcasts.utils import delete_storage_file


class PodcastLinkInline(admin.TabularInline):
    model = PodcastLink
    extra = 0


class PodcastChangeSlugForm(ModelForm):
    class Meta:
        fields = ["slug"]
        model = Podcast

    def clean_slug(self):
        slug = self.cleaned_data["slug"]
        if self.has_changed() and Podcast.objects.filter(slug=slug).exists():
            raise ValidationError(f"Another podcast with slug={slug} exists.")
        return slug

    def save(self, commit=True):
        if commit and self.has_changed():
            assert isinstance(self.instance, Podcast)
            old_instance = Podcast.objects.get(slug=self.initial["slug"])
            self.instance.save()
            self.instance.refresh_from_db()
            self.instance.authors.set(old_instance.authors.all())
            self.instance.categories.set(old_instance.categories.all())
            self.instance.links.set(old_instance.links.all())
            PodcastRequestLog.objects.filter(podcast=old_instance).update(podcast=self.instance)
            PodcastRssRequestLog.objects.filter(podcast=old_instance).update(podcast=self.instance)
            PodcastContent.objects.filter(podcast=old_instance).update(podcast=self.instance)
            old_instance.delete()
        return self.instance


@admin.register(Podcast)
class PodcastAdmin(admin.ModelAdmin):
    add_fields = (
        ("name", "slug"),
        "tagline",
        ("cover", "banner"),
        "favicon",
        "language",
        "description",
        "categories",
    )
    fields = (
        ("name", "slug"),
        "tagline",
        ("cover", "banner"),
        "favicon",
        "language",
        ("name_font_family", "name_font_size"),
        ("enable_comments", "require_comment_approval"),
        "owner",
        "description",
        "categories",
        "authors",
    )
    filter_horizontal = ["categories", "authors"]
    formfield_overrides = {
        MartorField: {"widget": AdminMartorWidget},
    }
    inlines = [PodcastLinkInline]
    list_display = (
        "name",
        "slug",
        "owner_link",
        "author_links",
        "view_count",
        "total_view_count",
        "play_count",
        "frontend_link",
    )
    readonly_fields = ("slug",)
    save_on_top = True

    @admin.display(description="authors")
    def author_links(self, obj: Podcast):
        return mark_safe(
            "<br>".join(
                format_html(
                    '<a class="nowrap" href="{url}">{user}</a>',
                    url=reverse("admin:users_user_change", args=(u.pk,)),
                    user=str(u),
                ) for u in obj.authors.all()
            )
        )

    def change_slug_view(self, request: HttpRequest, object_id):
        obj = self.get_object(request, unquote(object_id))

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            return self._get_obj_does_not_exist_redirect(request, self.opts, object_id)

        if request.method == "POST":
            form = PodcastChangeSlugForm(request.POST, instance=obj)
            if form.is_valid():
                form.save(commit=True)
                self.message_user(request, "The slug was changed.")
                return HttpResponseRedirect(
                    add_preserved_filters(
                        {
                            "preserved_filters": self.get_preserved_filters(request),
                            "opts": self.opts,
                        },
                        reverse(
                            f"admin:{self.opts.app_label}_{self.opts.model_name}_changelist",
                            current_app=self.admin_site.name,
                        ),
                    )
                )
        else:
            form = PodcastChangeSlugForm(instance=obj)

        return TemplateResponse(
            request=request,
            template=f"admin/{self.opts.app_label}/{self.opts.model_name}/change_slug.html",
            context={
                "opts": self.opts,
                "form": form,
            },
        )

    def frontend_link(self, obj: Podcast):
        return mark_safe(f'<a href="{obj.frontend_url}" target="_blank">{obj.frontend_url}</a>')

    def get_fields(self, request, obj=None):
        if obj:
            return self.fields
        return self.add_fields

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .prefetch_related("authors")
            .select_related("owner")
            .alias(content_view_count=Count("contents__requests", distinct=True))
            .annotate(
                view_count=Count("requests", distinct=True),
                total_view_count=F("content_view_count") + F("view_count"),
                play_count=Subquery(
                    PodcastContentAudioRequestLog.objects
                    .exclude(user_agent_type=AbstractRequestLog.UserAgentType.BOT)
                    .get_play_count_query(episode__podcast=OuterRef("slug"))
                ),
            )
        )

    def get_urls(self):
        from django.urls import path

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)

            setattr(wrapper, "model_admin", self)
            return update_wrapper(wrapper, view)

        return [
            path(
                "<path:object_id>/change_slug/",
                wrap(self.change_slug_view),
                name=f"{self.opts.app_label}_{self.opts.model_name}_change_slug",
            ),
        ] + super().get_urls()

    def has_change_permission(self, request, obj=None):
        return (
            request.user.is_superuser or
            obj is None or
            request.user == obj.owner or
            request.user in obj.authors.all()
        )

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    @admin.display(description="owner")
    def owner_link(self, obj: Podcast):
        return format_html(
            '<a class="nowrap" href="{url}">{user}</a>',
            url=reverse("admin:users_user_change", args=(obj.owner.pk,)),
            user=str(obj.owner),
        )

    @admin.display(description="plays", ordering="play_count")
    def play_count(self, obj):
        return round(obj.play_count, 3) if obj.play_count else 0.0

    def save_form(self, request, form, change):
        instance: Podcast = super().save_form(request, form, change)

        if not change:
            instance.authors.add(request.user)
            instance.owner = request.user
        if "cover" in form.changed_data:
            if "cover" in form.initial:
                delete_storage_file(form.initial["cover"])
            instance.handle_uploaded_cover()
        if "banner" in form.changed_data:
            if "banner" in form.initial:
                delete_storage_file(form.initial["banner"])
            instance.handle_uploaded_banner()
        if "favicon" in form.changed_data:
            if "favicon" in form.initial:
                delete_storage_file(form.initial["favicon"])
            if form.cleaned_data["favicon"]:
                instance.favicon_content_type = form.cleaned_data["favicon"].content_type
            else:
                instance.favicon_content_type = None
            instance.handle_uploaded_favicon()

        return instance

    @admin.display(description="views recursive", ordering="total_view_count")
    def total_view_count(self, obj):
        return obj.total_view_count

    @admin.display(description="views", ordering="view_count")
    def view_count(self, obj):
        return obj.view_count


class EpisodeSongInline(admin.TabularInline):
    autocomplete_fields = ["artists"]
    fields = ["episode", "timestamp", "name", "artists", "comment"]
    form = EpisodeSongForm
    model = EpisodeSong

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "artists":
            kwargs["queryset"] = Artist.objects.all()
            kwargs["widget"] = ArtistAutocompleteWidget(
                field=db_field,
                admin_site=self.admin_site,
                using=kwargs.get("using"),
            )
            kwargs["required"] = False
            return ArtistMultipleChoiceField(**kwargs)

        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def get_extra(self, request, obj=None, **kwargs):
        if obj is None:
            return 10
        return 3

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("artists")


class BasePodcastContentAdmin(admin.ModelAdmin):
    formfield_overrides = {
        MartorField: {"widget": AdminMartorWidget},
    }
    save_on_top = True
    search_fields = ["name", "description", "slug"]

    def get_form(self, request, obj=None, change=False, **kwargs):
        Form = super().get_form(request, obj, change, **kwargs)
        field = Form.base_fields.get("podcast")
        if field and not request.user.is_superuser:
            field.queryset = field.queryset.filter(Q(authors=request.user) | Q(owner=request.user)).distinct()
        return Form

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related("podcast", "podcast__owner")
            .prefetch_related("podcast__authors")
            .annotate(view_count=Count("requests", distinct=True))
        )

    def has_change_permission(self, request, obj=None):
        return (
            request.user.is_superuser or
            obj is None or
            request.user == obj.podcast.owner or
            request.user in obj.podcast.authors.all()
        )

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)


@admin.register(Episode)
class EpisodeAdmin(BasePodcastContentAdmin):
    fields = (
        ("podcast", "slug"),
        ("season", "number"),
        "name",
        ("is_draft", "published"),
        "audio_file",
        "image",
        "description",
        "duration_seconds",
        "audio_content_type",
        "audio_file_length",
    )
    inlines = [EpisodeSongInline]
    list_display = (
        "name",
        "season",
        "number",
        "is_visible",
        "is_draft",
        "podcast_link",
        "published",
        "view_count",
        "play_count",
    )
    list_filter = ["is_draft", "published", "podcast"]
    readonly_fields = ("duration_seconds", "audio_content_type", "audio_file_length", "slug")
    search_fields = ["name", "description", "slug", "songs__name", "songs__artists__name"]

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .annotate(
                play_count=Subquery(
                    PodcastContentAudioRequestLog.objects
                    .exclude(user_agent_type=AbstractRequestLog.UserAgentType.BOT)
                    .get_play_count_query(episode=OuterRef("pk"))
                ),
            )
        )

    def handle_audio_file(self, instance: Episode, audio_file: UploadedFile):
        suffix = "." + audio_file.name.split(".")[-1]

        # pylint: disable=consider-using-with
        file = tempfile.NamedTemporaryFile(suffix=suffix)
        file.write(audio_file.read())
        file.seek(0)

        info = mediainfo(file.name)
        instance.duration_seconds = float(info["duration"])
        instance.audio_content_type = audio_file.content_type
        instance.audio_file_length = audio_file.size

        Thread(
            target=self.update_audio_file_dbfs_array,
            kwargs={"file": file, "format_name": info["format_name"], "instance": instance},
        ).start()

    @admin.display(description="plays", ordering="play_count")
    def play_count(self, obj):
        return round(obj.play_count, 3) if obj.play_count else 0.0

    @admin.display(description="podcast", ordering="podcast")
    def podcast_link(self, obj: Episode):
        return format_html(
            '<a class="nowrap" href="{url}">{name}</a>',
            url=reverse("admin:podcasts_podcast_change", args=(obj.podcast.pk,)),
            name=str(obj.podcast),
        )

    def save_form(self, request, form, change):
        instance: Episode = super().save_form(request, form, change)

        if "image" in form.changed_data:
            if "image" in form.initial:
                delete_storage_file(form.initial["image"])
            instance.handle_uploaded_image()
        if "audio_file" in form.changed_data:
            if "audio_file" in form.initial:
                delete_storage_file(form.initial["audio_file"])
            if form.cleaned_data["audio_file"]:
                self.handle_audio_file(instance, form.cleaned_data["audio_file"])
            else:
                instance.duration_seconds = 0.0
                instance.audio_content_type = ""
                instance.audio_file_length = 0
                instance.dbfs_array = []

        return instance

    def update_audio_file_dbfs_array(self, instance: Episode, file: BinaryIO, format_name: str):
        instance.update_audio_file_dbfs_array(file=file, format_name=format_name, save=True)
        file.close()
        print("update_audio_file_dbfs_array finished")

    @admin.display(description="views", ordering="view_count")
    def view_count(self, obj):
        return obj.view_count


@admin.register(Post)
class PostAdmin(BasePodcastContentAdmin):
    fields = (
        "podcast",
        "name",
        ("is_draft", "published"),
        "description",
    )
    list_display = ("name", "is_visible", "is_draft", "podcast", "published")


class ArtistSongCountFilter(admin.SimpleListFilter):
    parameter_name = "song_count"
    title = "song count"

    def lookups(self, request, model_admin):
        return [
            ("0", "0"),
            ("1", "1"),
            ("2-10", "2-10"),
            ("10-", "10+"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "0":
            return queryset.filter(song_count=0)
        if self.value() == "1":
            return queryset.filter(song_count=1)
        if self.value() == "2-10":
            return queryset.filter(song_count__gte=2, song_count__lte=10)
        if self.value() == "10-":
            return queryset.filter(song_count__gt=10)
        return queryset


class ArtistSongInline(admin.TabularInline):
    extra = 0
    fields = ["song", "episode"]
    model = EpisodeSong.artists.through
    readonly_fields = ["song", "episode"]
    verbose_name = "song"
    verbose_name_plural = "songs"

    def episode(self, obj):
        return obj.episodesong.episode

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("episodesong__episode")

    def has_add_permission(self, request, obj):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def song(self, obj):
        return obj.episodesong.name


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    inlines = [ArtistSongInline]
    list_display = ["name", "song_count"]
    list_filter = [ArtistSongCountFilter]
    save_on_top = True
    search_fields = ["name"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(song_count=models.Count("songs"))

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser or obj is None:
            return True
        return not (
            Podcast.objects
            .filter(contents__episode__songs__artists=obj)
            .exclude(Q(authors=request.user) | Q(owner=request.user))
            .exists()
        )

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    @admin.display(description="songs", ordering="song_count")
    def song_count(self, obj):
        return obj.song_count


@admin.register(EpisodeSong)
class EpisodeSongAdmin(admin.ModelAdmin):
    filter_horizontal = ["artists"]
    form = EpisodeSongForm
    list_display = ["name", "artists_str", "episode_str", "timestamp_str"]
    ordering = ["-episode__number", "timestamp"]
    save_on_top = True
    search_fields = ["name", "artists__name", "comment"]

    @admin.display(description="artists")
    def artists_str(self, obj: EpisodeSong):
        return mark_safe(
            "<br>".join(
                format_html(
                    '<a href="{url}">{name}</a>',
                    url=reverse("admin:podcasts_artist_change", args=(a.pk,)),
                    name=a.name,
                ) for a in obj.artists.all()
            )
        )

    @admin.display(description="episode", ordering="episode__number")
    def episode_str(self, obj: EpisodeSong):
        return format_html(
            '<a href="{url}">{name}</a>',
            url=reverse("admin:podcasts_episode_change", args=(obj.episode.pk,)),
            name=str(obj.episode),
        )

    def get_form(self, request, obj=None, change=False, **kwargs):
        Form = super().get_form(request, obj, change, **kwargs)
        field = Form.base_fields.get("episode")
        if field:
            field.queryset = (
                field.queryset
                .filter(Q(podcast__authors=request.user) | Q(podcast__owner=request.user))
                .distinct()
            )
        return Form

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .prefetch_related("artists", "episode__podcast__authors")
            .select_related("episode__podcast__owner")
        )

    def has_change_permission(self, request, obj=None):
        return (
            request.user.is_superuser or
            obj is None or
            request.user == obj.episode.podcast.owner or
            request.user in obj.episode.podcast.authors.all()
        )

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    @admin.display(description="timestamp", ordering="timestamp")
    def timestamp_str(self, obj: EpisodeSong):
        return seconds_to_timestamp(obj.timestamp)


@admin.action(description="Approve comments")
def approve_comments(modeladmin, request, queryset):
    queryset.update(is_approved=True)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    actions = [approve_comments]
    list_display = ["name", "truncated_text", "created", "is_approved", "content_link"]
    list_filter = ["is_approved", "podcast_content__podcast"]
    readonly_fields = ["podcast_content", "name", "text"]

    @admin.display(description="content")
    def content_link(self, obj: Comment):
        content_class = obj.podcast_content.get_real_instance_class()
        if content_class is Episode:
            view = "admin:podcasts_episode_change"
        elif content_class is Post:
            view = "admin:podcasts_post_change"
        else:
            return ""

        return format_html(
            '<a href="{url}">{name}</a>',
            url=reverse(view, args=(obj.podcast_content.pk,)),
            name=str(obj.podcast_content),
        )

    def get_form(self, request, obj=None, change=False, **kwargs):
        Form = super().get_form(request, obj, change, **kwargs)
        field = Form.base_fields.get("podcast_content")
        if field:
            field.queryset = (
                field.queryset
                .filter(Q(podcast__authors=request.user) | Q(podcast__owner=request.user))
                .distinct()
            )
        return Form

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .prefetch_related("podcast_content__podcast__authors")
            .select_related("podcast_content__podcast__owner")
        )

    def has_change_permission(self, request, obj=None):
        return (
            request.user.is_superuser or
            obj is None or
            request.user == obj.podcast_content.podcast.owner or
            request.user in obj.podcast_content.podcast.authors.all()
        )

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    @admin.display(description="text")
    def truncated_text(self, obj: Comment):
        if len(obj.text) > 1000:
            return obj.text[:1000] + "..."
        return obj.text
