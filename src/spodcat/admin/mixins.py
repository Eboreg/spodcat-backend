from django.forms import TimeInput

from spodcat.utils.model_fields import TimestampField
from spodcat.utils.model_mixin import ModelMixin


class AdminMixin:
    formfield_overrides = {TimestampField: {"widget": TimeInput}}

    class Media:
        css = {"all": ["spodcat/css/admin.css"]}
        js = ["spodcat/js/admin.js"]

    def has_change_permission(self, request, obj=None):
        return obj is None or (isinstance(obj, ModelMixin) and obj.has_change_permission(request))

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)
