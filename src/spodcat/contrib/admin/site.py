from django.apps import apps
from django.contrib import admin
from django.contrib.auth.models import AbstractUser
from django.db.models import Q


class AdminSite(admin.AdminSite):
    final_catch_all_view = False

    def each_context(self, request):
        context = super().each_context(request)
        context["logs_app_installed"] = apps.is_installed("spodcat.logs")
        return context

    def index(self, request, extra_context=None):
        from spodcat.models import Comment

        extra_context = extra_context or {}
        comment_qs = Comment.objects.filter(is_approved=False).order_by("-created").select_related("podcast_content")
        if not isinstance(request.user, AbstractUser) or not request.user.is_superuser:
            comment_qs = comment_qs.filter(
                Q(podcast_content__podcast__owner=request.user) | Q(podcast_content__podcast__authors=request.user)
            )
        extra_context["comments_awaiting_approval"] = comment_qs
        return super().index(request, extra_context)
