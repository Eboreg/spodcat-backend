from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from django.apps import apps
from django.contrib import admin
from django.db.models import Model

from spodcat.contrib.admin.mixin import AdminMixin
from spodcat.settings import spodcat_settings


if TYPE_CHECKING:
    from collections.abc import Iterable

    from django.db.models import QuerySet
    from django.http import HttpRequest, HttpResponse


_ModelT = TypeVar("_ModelT", bound=Model)


class SpodcatModelAdmin(AdminMixin, admin.ModelAdmin):
    def change_view(
        self,
        request: HttpRequest,
        object_id: str,
        form_url: str = "",
        extra_context: dict[str, Any] | None = None,
    ) -> HttpResponse:
        extra_context = extra_context or {}
        extra_context.update(logs_app_installed=apps.is_installed("spodcat.logs"))
        return super().change_view(request=request, object_id=object_id, form_url=form_url, extra_context=extra_context)


class SpodcatStaticRSSModelAdmin(SpodcatModelAdmin, Generic[_ModelT]):
    def delete_model(self, request, obj: _ModelT):
        super().delete_model(request, obj)
        if spodcat_settings.STATIC_RSS_XML:
            if slugs := self.get_podcast_slugs_from_instance(obj):
                self.regenerate_static_rss(slugs)

    def delete_queryset(self, request, queryset: QuerySet[_ModelT]):
        super().delete_queryset(request, queryset)
        if spodcat_settings.STATIC_RSS_XML:
            if slugs := self.get_podcast_slugs_from_queryset(queryset):
                self.regenerate_static_rss(slugs)

    @abstractmethod
    def get_podcast_slugs_from_instance(self, obj: _ModelT) -> Iterable[str]: ...

    @abstractmethod
    def get_podcast_slugs_from_queryset(self, queryset: QuerySet[_ModelT]) -> Iterable[str]: ...

    def regenerate_static_rss(self, podcast_slugs: Iterable[str]):
        from spodcat.rss import PodcastRssData

        for slug in podcast_slugs:
            data = PodcastRssData(slug)
            data.regenerate_static()

    def save_model(self, request, obj: _ModelT, form, change):
        super().save_model(request, obj, form, change)
        if spodcat_settings.STATIC_RSS_XML:
            if slugs := self.get_podcast_slugs_from_instance(obj):
                self.regenerate_static_rss(slugs)
