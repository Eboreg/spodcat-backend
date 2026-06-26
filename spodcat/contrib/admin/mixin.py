from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from django.db.models import Model, QuerySet
from django.forms import TimeInput
from django.urls import reverse
from django.utils.html import format_html
from martor.models import MartorField
from polymorphic.models import PolymorphicModel

from spodcat.contrib.admin.site import AdminSite
from spodcat.contrib.admin.widgets import AdminMartorWidget
from spodcat.model_fields import TimestampField
from spodcat.model_mixin import ModelMixin
from spodcat.settings import spodcat_settings


_ModelT = TypeVar("_ModelT", bound=Model)


if TYPE_CHECKING:
    from django.contrib.admin import ModelAdmin

    class MixinBase(ModelAdmin, Generic[_ModelT]): ...
else:

    class MixinBase(Generic[_ModelT]): ...


class AdminMixin:
    admin_site: AdminSite
    formfield_overrides = {
        TimestampField: {"widget": TimeInput},
        MartorField: {"widget": AdminMartorWidget},
    }

    class Media:
        css = {"all": ["spodcat/css/admin.css"]}
        js = ["spodcat/js/admin.js"]

    def get_change_link(self, obj: Model, text: str | None = None, **params):
        if text is None:
            text = str(obj)

        if not self.admin_site.is_registered(obj.__class__):
            return text

        return format_html(
            '<a class="nowrap" href="{url}">{text}</a>',
            url=self.get_change_url(obj=obj, **params),
            text=text,
        )

    def get_change_url(self, obj: Model, **params):
        meta = obj._meta

        if isinstance(obj, PolymorphicModel):
            klass = obj.get_real_instance_class()
            if klass:
                meta = klass._meta

        return reverse(f"admin:{meta.app_label}_{meta.model_name}_change", args=(obj.pk,), query=params)

    def get_changelist_link(self, model: type[Model], text: Any, **params):
        return format_html(
            '<a class="nowrap" href="{url}">{text}</a>',
            url=self.get_changelist_url(model=model, **params),
            text=text,
        )

    def get_changelist_url(self, model: type[Model], **params):
        return reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist", query=params)

    def has_change_permission(self, request, obj=None):
        return obj is None or (isinstance(obj, ModelMixin) and obj.has_change_permission(request))

    def has_delete_permission(self, request, obj=None):
        if isinstance(obj, ModelMixin):
            return obj.has_delete_permission(request)

        return self.has_change_permission(request, obj)


class StaticRSSMixin(MixinBase[_ModelT]):
    def delete_model(self, request, obj: _ModelT):
        super().delete_model(request, obj)
        if slugs := self.get_podcast_slugs_from_instance(obj):
            self.regenerate_static_rss(slugs)

    def delete_queryset(self, request, queryset: QuerySet[_ModelT]):
        super().delete_queryset(request, queryset)
        if slugs := self.get_podcast_slugs_from_queryset(queryset):
            self.regenerate_static_rss(slugs)

    def get_podcast_slugs_from_instance(self, obj: _ModelT) -> Iterable[str]:
        return []

    def get_podcast_slugs_from_queryset(self, queryset: QuerySet[_ModelT]) -> Iterable[str]:
        return []

    def regenerate_static_rss(self, podcast_slugs: Iterable[str]):
        if spodcat_settings.STATIC_RSS_XML:
            from spodcat.rss import PodcastRssData

            for slug in podcast_slugs:
                data = PodcastRssData(slug)
                data.regenerate_static()

    def save_model(self, request, obj: _ModelT, form, change):
        super().save_model(request, obj, form, change)
        if slugs := self.get_podcast_slugs_from_instance(obj):
            self.regenerate_static_rss(slugs)
