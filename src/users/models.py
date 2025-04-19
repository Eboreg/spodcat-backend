from django.contrib.auth.models import AbstractUser

from model_mixin import ModelMixin


class User(ModelMixin, AbstractUser):
    ...
