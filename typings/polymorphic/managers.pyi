from typing import TypeVar

from django.db import models
from polymorphic.models import PolymorphicModel


_PM = TypeVar("_PM", bound=PolymorphicModel)


class PolymorphicManager(models.Manager[_PM]):
    ...
