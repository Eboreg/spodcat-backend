from django.forms import TimeInput
from django.http import HttpRequest

from utils.model_fields import TimestampField
from utils.model_mixin import ModelMixin


class AdminMixin:
    formfield_overrides = {TimestampField: {"widget": TimeInput}}

    class Media:
        css = {"all": ["assets/css/admin.css"]}
        js = ["assets/js/admin.js"]

    def has_change_permission(self, request: HttpRequest, obj: ModelMixin | None = None):
        return obj is None or obj.has_change_permission(request)

    def has_delete_permission(self, request, obj: ModelMixin | None = None):
        return self.has_change_permission(request, obj)
