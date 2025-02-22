import tempfile
from io import BytesIO
from threading import Thread
from typing import BinaryIO

from django.contrib import admin
from django.core.files.uploadedfile import UploadedFile
from django.db import models
from mdeditor.widgets import MDEditorWidget
from PIL import Image
from pydub.utils import mediainfo

from podcasts.models import Episode, Podcast, PodcastLink


class PodcastLinkInline(admin.TabularInline):
    model = PodcastLink
    extra = 0


@admin.register(Podcast)
class PodcastAdmin(admin.ModelAdmin):
    filter_horizontal = ["categories", "owners"]
    fields = (
        ("name", "slug"),
        "tagline",
        ("cover", "banner"),
        "favicon",
        "language",
        "description",
        "categories",
    )
    formfield_overrides = {
        models.TextField: {"widget": MDEditorWidget},
    }
    inlines = [PodcastLinkInline]

    def handle_banner(self, instance: Podcast):
        if instance.banner and instance.banner.width > 960 and instance.banner.height > 320:
            ratio = max(960 / instance.banner.width, 320 / instance.banner.height)
            buf = BytesIO()

            with Image.open(instance.banner) as im:
                im.thumbnail((int(instance.banner.width * ratio), int(instance.banner.height * ratio)))
                im.save(buf, format=im.format)

            instance.banner.save(name=instance.banner.name, content=buf, save=False)

    def handle_cover(self, instance: Podcast):
        if instance.cover:
            stem, suffix = instance.cover.name.rsplit(".", maxsplit=1)
            filename = f"{stem}-thumbnail.{suffix}"
            buf = BytesIO()

            with Image.open(instance.cover) as im:
                ratio = 150 / max(im.width, im.height)
                im.thumbnail((int(im.width * ratio), int(im.height * ratio)))
                im.save(buf, format=im.format)

            instance.cover_thumbnail.save(name=filename, content=buf, save=False)

        else:
            instance.cover_thumbnail.delete(save=False)

    def handle_favicon(self, instance: Podcast, file: UploadedFile | None):
        if file:
            instance.favicon_content_type = file.content_type

        if instance.favicon:
            if instance.favicon.width > 100 and instance.favicon.height > 100:
                ratio = max(100 / instance.favicon.width, 100 / instance.favicon.height)
                buf = BytesIO()

                with Image.open(instance.favicon) as im:
                    im.thumbnail((int(instance.favicon.width * ratio), int(instance.favicon.height * ratio)))
                    im.save(buf, format=im.format)

                instance.favicon.save(name=instance.favicon.name, content=buf, save=False)
        else:
            instance.favicon_content_type = None

    def save_form(self, request, form, change):
        instance: Podcast = super().save_form(request, form, change)

        if "cover" in form.changed_data:
            self.handle_cover(instance)

        if "banner" in form.changed_data:
            self.handle_banner(instance)

        if "favicon" in form.changed_data:
            self.handle_favicon(instance, form.cleaned_data["favicon"])

        return instance


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = ("name", "episode", "is_published", "podcast", "created", "duration_seconds")
    formfield_overrides = {
        models.TextField: {"widget": MDEditorWidget},
    }
    fields = (
        "podcast",
        "episode",
        "name",
        "audio_file",
        "description",
        "published",
        "duration_seconds",
        "audio_content_type",
        "audio_file_length",
    )
    readonly_fields = ("duration_seconds", "audio_content_type", "audio_file_length")

    def save_form(self, request, form, change):
        instance: Episode = super().save_form(request, form, change)

        if "audio_file" in form.changed_data:
            audio_file: UploadedFile = form.cleaned_data["audio_file"]
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

        return instance

    def update_audio_file_dbfs_array(self, instance: Episode, file: BinaryIO, format_name: str):
        instance.update_audio_file_dbfs_array(file=file, format_name=format_name, save=True)
        file.close()
