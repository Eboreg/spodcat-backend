from typing import Any
from urllib.parse import urlencode

from django.contrib.admin import AdminSite
from django.db.models import Model
from django.forms import TimeInput
from django.urls import reverse
from django.utils.html import format_html
from polymorphic.models import PolymorphicModel

from spodcat.model_fields import TimestampField
from spodcat.model_mixin import ModelMixin


class AdminMixin:
    admin_site: AdminSite
    formfield_overrides = {TimestampField: {"widget": TimeInput}}

    class Media:
        css = {"all": ["spodcat/css/admin.css"]}
        js = ["spodcat/js/admin.js"]

    def get_change_link(self, obj: Model | None, text: str | None = None, **params):
        if obj is None:
            return None

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
        meta = obj.get_real_instance_class()._meta if isinstance(obj, PolymorphicModel) else obj._meta
        url = reverse(f"admin:{meta.app_label}_{meta.model_name}_change", args=(obj.pk,))
        if params:
            url += "?" + urlencode(params)
        return url

    def get_changelist_link(self, model: type[Model], text: Any, **params):
        return format_html(
            '<a class="nowrap" href="{url}">{text}</a>',
            url=self.get_changelist_url(model=model, **params),
            text=text,
        )

    def get_changelist_url(self, model: type[Model], **params):
        url = reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist")
        if params:
            url += "?" + urlencode(params)
        return url

    def has_change_permission(self, request, obj=None):
        return obj is None or (isinstance(obj, ModelMixin) and obj.has_change_permission(request))

    def has_delete_permission(self, request, obj=None):
        if isinstance(obj, ModelMixin):
            return obj.has_delete_permission(request)

        return self.has_change_permission(request, obj)
