from django.core.exceptions import ValidationError
from django.db.models.fields.files import ImageFieldFile


def podcast_cover_validator(value: ImageFieldFile):
    if value.height < 1400 or value.width < 1400:
        raise ValidationError("Cover image width and height should be >= 1400px")
