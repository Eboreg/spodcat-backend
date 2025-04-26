from typing import Self, TypeVar

from django.db.models import QuerySet
from polymorphic.models import PolymorphicModel


_PM = TypeVar("_PM", bound=PolymorphicModel)


class PolymorphicQuerySet(QuerySet[_PM]):
    def non_polymorphic(self) -> Self: ...
    def instance_of(self, *args: PolymorphicModel) -> Self: ...
    def not_instance_of(self, *args: PolymorphicModel) -> Self: ...
    def get_real_instances(self, base_result_objects=None) -> Self: ...
