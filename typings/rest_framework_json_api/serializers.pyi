from collections.abc import Mapping
from typing import TypeVar

# star import defined so `rest_framework_json_api.serializers` can be
# a simple drop in for `rest_framework.serializers`
# from rest_framework.serializers import *  # noqa: F401, F403
from django.db.models import Model
from rest_framework.serializers import (
    BaseSerializer,
    BooleanField as BooleanField,
    CharField as CharField,
    ChoiceField as ChoiceField,
    DateField as DateField,
    DateTimeField as DateTimeField,
    DecimalField as DecimalField,
    DictField as DictField,
    DurationField as DurationField,
    EmailField as EmailField,
    Field as Field,
    FileField as FileField,
    FilePathField as FilePathField,
    FloatField as FloatField,
    HiddenField as HiddenField,
    HStoreField as HStoreField,
    HyperlinkedModelSerializer as HyperlinkedModelSerializerBase,
    ImageField as ImageField,
    IntegerField as IntegerField,
    IPAddressField as IPAddressField,
    JSONField as JSONField,
    ListField as ListField,
    ModelField as ModelField,
    ModelSerializer as ModelSerializerBase,
    MultipleChoiceField as MultipleChoiceField,
    PrimaryKeyRelatedField as PrimaryKeyRelatedField,
    ReadOnlyField as ReadOnlyField,
    RegexField as RegexField,
    Serializer as SerializerBase,
    SerializerMetaclass as SerializerMetaclassBase,
    SerializerMethodField as SerializerMethodField,
    SkipField as SkipField,
    SlugField as SlugField,
    TimeField as TimeField,
    URLField as URLField,
    UUIDField as UUIDField,
    ValidationError as ValidationError,
)

_MT = TypeVar("_MT", bound=Model)  # Model Type
_IN = TypeVar("_IN")  # Instance Type

class ResourceIdentifierObjectSerializer(BaseSerializer): ...
class SparseFieldsetsMixin: ...
class IncludedResourcesValidationMixin: ...
class ReservedFieldNamesMixin: ...
class LazySerializersDict(Mapping): ...
class SerializerMetaclass(SerializerMetaclassBase): ...
class Serializer(
    IncludedResourcesValidationMixin,
    SparseFieldsetsMixin,
    ReservedFieldNamesMixin,
    SerializerBase[_IN],
    metaclass=SerializerMetaclass,
): ...
class HyperlinkedModelSerializer(
    IncludedResourcesValidationMixin,
    SparseFieldsetsMixin,
    ReservedFieldNamesMixin,
    HyperlinkedModelSerializerBase[_MT],
    metaclass=SerializerMetaclass,
): ...
class ModelSerializer(
    IncludedResourcesValidationMixin,
    SparseFieldsetsMixin,
    ReservedFieldNamesMixin,
    ModelSerializerBase[_MT],
    metaclass=SerializerMetaclass,
): ...
class PolymorphicSerializerMetaclass(SerializerMetaclass): ...

class PolymorphicModelSerializer(ModelSerializer[_MT], metaclass=PolymorphicSerializerMetaclass):
    @classmethod
    def get_polymorphic_serializer_for_instance(cls, instance): ...
    @classmethod
    def get_polymorphic_model_for_serializer(cls, serializer): ...
    @classmethod
    def get_polymorphic_serializer_for_type(cls, obj_type): ...
    @classmethod
    def get_polymorphic_model_for_type(cls, obj_type): ...
    @classmethod
    def get_polymorphic_types(cls): ...
