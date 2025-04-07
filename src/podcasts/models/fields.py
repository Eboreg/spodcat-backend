from azure.core.exceptions import ResourceNotFoundError
from django.db import models


class ImageField(models.ImageField):
    # pylint: disable=keyword-arg-before-vararg
    def update_dimension_fields(self, instance, force=False, *args, **kwargs):
        try:
            super().update_dimension_fields(instance, force, *args, **kwargs)
        except ResourceNotFoundError:
            if self.width_field:
                setattr(instance, self.width_field, None)
            if self.height_field:
                setattr(instance, self.height_field, None)
