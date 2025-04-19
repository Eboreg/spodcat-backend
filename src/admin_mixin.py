from django.http import HttpRequest

from model_mixin import ModelMixin


class AdminMixin:
    def has_change_permission(self, request: HttpRequest, obj: ModelMixin | None = None):
        return obj is None or obj.has_change_permission(request)

    def has_delete_permission(self, request, obj: ModelMixin | None = None):
        return self.has_change_permission(request, obj)
