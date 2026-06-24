from typing import Any, ClassVar, Generic, TypeVar

from django.db.models import Model
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import ViewSetMixin


_MT = TypeVar("_MT", bound=Model)
_PT = TypeVar("_PT", bound=Model)


class NestedMixin:
    kwargs: dict[str, Any]
    parent_lookup: ClassVar[str]  # "podcast" for episode view
    parent_url_kwarg: ClassVar[str | None] = None
    parent_view: ClassVar[type[GenericAPIView]]

    @classmethod
    def get_parent_lookup_keys(cls, prefix: str = ""):
        if prefix and not prefix.endswith("__"):
            prefix += "__"

        fk = f"{prefix}{cls.parent_lookup}__{cls.parent_view.lookup_field}"
        url_kwarg = cls.parent_url_kwarg or f"{cls.parent_lookup}_{cls.parent_view.lookup_field}"

        if issubclass(cls.parent_view, NestedMixin):
            return {fk: url_kwarg, **cls.parent_view.get_parent_lookup_keys(prefix + cls.parent_lookup)}

        return {fk: url_kwarg}

    def get_parent_lookup_kwargs(self):
        return {fk: self.kwargs[kw] for fk, kw in self.get_parent_lookup_keys().items()}


class NestedCreateModelMixin(CreateModelMixin, NestedMixin):
    def perform_create(self, serializer: BaseSerializer):
        serializer.save(**self.get_parent_lookup_kwargs())


class NestedGenericAPIView(NestedMixin, GenericAPIView[_MT], Generic[_MT, _PT]):
    def get_queryset(self):
        return super().get_queryset().filter(**self.get_parent_lookup_kwargs())


class NestedGenericViewSet(ViewSetMixin, NestedGenericAPIView[_MT, _PT]):
    ...


class NestedReadOnlyModelViewSet(RetrieveModelMixin, ListModelMixin, NestedGenericViewSet[_MT, _PT]):
    ...
