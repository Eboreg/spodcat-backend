from functools import update_wrapper

from django.apps import apps
from django.contrib import admin
from django.db.models import Q
from django.http import HttpRequest
from django.urls import path, reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from spodcat.models.podcast import spodcat_settings


class AdminSite(admin.AdminSite):
    final_catch_all_view = False

    def index(self, request, extra_context=None):
        from spodcat.models import Comment

        extra_context = extra_context or {}
        comment_qs = Comment.objects.filter(is_approved=False).order_by("-created").select_related("podcast_content")
        if not request.user.is_superuser:
            comment_qs = comment_qs.filter(
                Q(podcast_content__podcast__owner=request.user) | Q(podcast_content__podcast__authors=request.user)
            )
        extra_context["comments_awaiting_approval"] = comment_qs
        return super().index(request, extra_context)

    def get_urls(self):
        def wrap(view, cacheable=False):
            def wrapper(*args, **kwargs):
                return self.admin_view(view, cacheable)(*args, **kwargs)

            setattr(wrapper, "admin_site", self)
            setattr(wrapper, "login_url", reverse_lazy("admin:login", current_app=self.name))

            return update_wrapper(wrapper, view)

        return super().get_urls() + [
            path("charts/", wrap(self.charts), name="charts"),
        ]

    def charts(self, request: HttpRequest):
        from spodcat.models import Podcast

        context = {
            "podcasts": Podcast.objects.filter_by_user(request.user),
            "title": _("Charts"),
            "root_path": spodcat_settings.get_backend_root_path(),
            **self.each_context(request),
        }
        return TemplateView.as_view(template_name="admin/charts.html", extra_context=context)(request)

    def each_context(self, request):
        context = super().each_context(request)
        context["logs_app_installed"] = apps.is_installed("spodcat.logs")
        return context
