from django.contrib import admin
from django.db.models import Q
from django.http import HttpRequest
from django.urls import path
from django.views.generic import TemplateView

from podcasts.models import Comment, Podcast


class AdminSite(admin.AdminSite):
    final_catch_all_view = False

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        comment_qs = Comment.objects.filter(is_approved=False).order_by("-created").select_related("podcast_content")
        if not request.user.is_superuser:
            comment_qs = comment_qs.filter(
                Q(podcast_content__podcast__owner=request.user) | Q(podcast_content__podcast__authors=request.user)
            )
        extra_context["comments_awaiting_approval"] = comment_qs
        return super().index(request, extra_context)

    def get_urls(self):
        return super().get_urls() + [
            path("charts/", self.charts, name="charts"),
        ]

    def charts(self, request: HttpRequest):
        context = {
            "podcasts": Podcast.objects.filter_by_user(request.user),
            **self.each_context(request),
        }
        return TemplateView.as_view(template_name="admin/charts.html", extra_context=context)(request)
