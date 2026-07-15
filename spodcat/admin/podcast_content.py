from collections.abc import Iterable
from typing import Generic, TypeVar

from django.apps import apps
from django.contrib import admin
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Count, Q
from django.forms import ModelChoiceField, ModelForm
from django.http import HttpRequest
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from spodcat.contrib.admin.mixin import AdminMixin, StaticRSSMixin
from spodcat.forms import PodcastContentVideoAdminForm
from spodcat.models import PodcastContent, Video


_PCT = TypeVar("_PCT", bound=PodcastContent)


class PodcastContentVideoInline(AdminMixin, admin.TabularInline):
    model = Video
    extra = 1
    form = PodcastContentVideoAdminForm


class BasePodcastContentAdmin(AdminMixin, StaticRSSMixin[_PCT], admin.ModelAdmin, Generic[_PCT]):
    save_on_top = True
    search_fields = ["name", "description", "slug"]

    def get_form(self, request: HttpRequest, obj: _PCT | None = None, change: bool = False, **kwargs):
        Form = super().get_form(request, obj, change, **kwargs)
        field = Form.base_fields.get("podcast")
        if (
            isinstance(field, ModelChoiceField)
            and field.queryset is not None
            and (not isinstance(request.user, AbstractUser) or not request.user.is_superuser)
        ):
            field.queryset = field.queryset.filter(Q(authors=request.user) | Q(owner=request.user)).distinct()
        return Form

    def get_podcast_slugs_from_instance(self, obj: _PCT) -> list[str]:
        return [obj.podcast.slug]

    def get_podcast_slugs_from_queryset(self, queryset: models.QuerySet[_PCT, _PCT]) -> Iterable[str]:
        return set(queryset.values_list("podcast__slug", flat=True))

    def get_queryset(self, request: HttpRequest):
        qs = (
            super()
            .get_queryset(request)
            .select_related("podcast", "podcast__owner")
            .prefetch_related("podcast__authors")
        )

        if apps.is_installed("spodcat.logs"):
            return qs.annotate(view_count=Count("requests", distinct=True))

        return qs

    def get_readonly_fields(self, request: HttpRequest, obj: _PCT | None = None):
        fields = super().get_readonly_fields(request, obj)
        if obj is None:
            return ["slug", *fields]
        return fields

    def save_form(self, request: HttpRequest, form: ModelForm, change: bool):
        instance: _PCT = super().save_form(request, form, change)
        if not form.cleaned_data["is_draft"] and (not change or "is_draft" in form.changed_data):
            instance.published = now()
        return instance

    @admin.display(description=_("views"), ordering="view_count")
    def view_count(self, obj: _PCT):
        from spodcat.logs.models import PodcastContentRequestLog

        view_count: int = getattr(obj, "view_count", 0)

        if not view_count:
            return 0

        return self.get_changelist_link(
            model=PodcastContentRequestLog,
            text=view_count,
            content__id__exact=obj.pk,
        )
