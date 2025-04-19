from django.contrib.auth.models import AbstractUser

from model_mixin import ModelMixin


class User(ModelMixin, AbstractUser):
    def has_change_permission(self, request):
        return request.user.is_superuser or request.user == self
