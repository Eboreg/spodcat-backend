from django.contrib import admin
from django.db.models import Q

from podcasts.models import Comment


class AdminSite(admin.AdminSite):
    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        comment_qs = Comment.objects.filter(is_approved=False).order_by("-created").select_related("podcast_content")
        if not request.user.is_superuser:
            comment_qs = comment_qs.filter(
                Q(podcast_content__podcast__owner=request.user) | Q(podcast_content__podcast__authors=request.user)
            )
        extra_context["comments_awaiting_approval"] = comment_qs
        return super().index(request, extra_context)
