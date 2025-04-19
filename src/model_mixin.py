from typing import Any
from urllib.parse import urlencode

from django.db.models.options import Options
from django.urls import reverse
from django.utils.html import format_html
from polymorphic.models import PolymorphicModel


class ModelMixin:
    _meta: Options
    pk: Any

    @classmethod
    def get_admin_list_link(cls, text: Any, **params):
        return format_html(
            '<a class="nowrap" href="{url}">{text}</a>',
            url=cls.get_admin_list_url(**params),
            text=text,
        )

    @classmethod
    def get_admin_list_url(cls, **params):
        url = reverse(f"admin:{cls._meta.app_label}_{cls._meta.model_name}_changelist")
        if params:
            url += "?" + urlencode(params)
        return url

    def get_admin_link(self, text: Any | None = None, **params):
        if text is None:
            text = str(self)

        return format_html(
            '<a class="nowrap" href="{url}">{text}</a>',
            url=self.get_admin_url(**params),
            text=text,
        )

    def get_admin_url(self, **params):
        meta = self.get_real_instance_class()._meta if isinstance(self, PolymorphicModel) else self._meta
        url = reverse(f"admin:{meta.app_label}_{meta.model_name}_change", args=(self.pk,))
        if params:
            url += "?" + urlencode(params)
        return url
