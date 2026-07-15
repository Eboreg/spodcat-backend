from django.contrib import admin
from django.db import models
from django.http import HttpRequest
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from spodcat.contrib.admin.mixin import AdminMixin
from spodcat.models import Comment


@admin.action(description=_("Approve comments"))
def approve_comments(modeladmin: "CommentAdmin", request: HttpRequest, queryset: models.QuerySet[Comment]):
    queryset.update(is_approved=True)


class CommentAdmin(AdminMixin, admin.ModelAdmin):
    actions = [approve_comments]
    list_display = ["name", "truncated_text", "created", "is_approved", "content_link", "frontend_link"]
    list_filter = ["is_approved", "podcast_content__podcast"]
    readonly_fields = ["podcast_content", "name", "text"]

    @admin.display(description=_("content"))
    def content_link(self, obj: Comment):
        return self.get_change_link(obj.podcast_content)

    @admin.display(description="")
    def frontend_link(self, obj: Comment):
        return mark_safe(f'<a href="{obj.podcast_content.frontend_url}" target="_blank">' + _("Frontend") + "</a>")

    def get_queryset(self, request: HttpRequest):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("podcast_content__podcast__authors")
            .select_related("podcast_content__podcast__owner")
        )

    @admin.display(description=_("text"))
    def truncated_text(self, obj: Comment):
        if len(obj.text) > 1000:
            return obj.text[:1000] + "..."
        return obj.text
