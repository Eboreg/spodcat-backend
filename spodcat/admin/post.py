from django.apps import apps
from django.contrib import admin
from django.http import HttpRequest
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from spodcat.admin.podcast_content import BasePodcastContentAdmin, PodcastContentVideoInline
from spodcat.models import Post


class PostAdmin(BasePodcastContentAdmin[Post]):
    fields = [
        ("id", "slug"),
        ("name", "podcast"),
        ("is_draft", "published"),
        "description",
    ]
    inlines = [PodcastContentVideoInline]
    readonly_fields = ["id", "published"]

    @admin.display(description="")
    def frontend_link(self, obj: Post):
        return mark_safe(f'<a href="{obj.frontend_url}" target="_blank">' + _("Frontend") + "</a>")

    def get_list_display(self, request: HttpRequest):
        if apps.is_installed("spodcat.logs"):
            return [
                "name",
                "is_visible",
                "is_draft",
                "podcast",
                "published",
                "view_count",
                "frontend_link",
            ]
        return ["name", "is_visible", "is_draft", "podcast", "published", "frontend_link"]
