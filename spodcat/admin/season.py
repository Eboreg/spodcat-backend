from collections.abc import Iterable

from django.contrib import admin
from django.db import models
from django.forms import ModelForm
from django.http import HttpRequest

from spodcat.contrib.admin.mixin import AdminMixin, StaticRSSMixin
from spodcat.models import Season
from spodcat.utils import delete_storage_file


class SeasonAdmin(AdminMixin, StaticRSSMixin[Season], admin.ModelAdmin):
    list_display = ["podcast", "number", "name"]
    fields = ["podcast", "number", "name", "image"]

    def get_podcast_slugs_from_instance(self, obj: Season) -> Iterable[str]:
        return [obj.podcast.slug]

    def get_podcast_slugs_from_queryset(self, queryset: models.QuerySet[Season, Season]) -> Iterable[str]:
        return set(queryset.values_list("podcast__slug", flat=True))

    def save_form(self, request: HttpRequest, form: ModelForm, change: bool):
        instance: Season = super().save_form(request, form, change)

        if "image" in form.changed_data:
            if "image" in form.initial:
                delete_storage_file(form.initial["image"])
            instance.handle_uploaded_image()

        return instance
