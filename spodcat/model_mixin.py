from django.contrib.auth.models import AbstractUser
from django.http import HttpRequest


class ModelMixin:
    def has_change_permission(self, request: HttpRequest):
        return isinstance(request.user, AbstractUser) and request.user.is_superuser

    def has_delete_permission(self, request: HttpRequest):
        return self.has_change_permission(request)
