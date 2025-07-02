from django.http import HttpRequest


class ModelMixin:
    def has_change_permission(self, request: HttpRequest):
        return request.user.is_superuser

    def has_delete_permission(self, request: HttpRequest):
        return self.has_change_permission(request)
