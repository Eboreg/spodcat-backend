from django.core.exceptions import ValidationError
from django.db.models.fields.files import ImageFieldFile
from django.utils.translation import gettext as _


def podcast_cover_validator(value: ImageFieldFile):
    if value.height < 1400 or value.width < 1400:
        raise ValidationError(_("Cover image width and height should be >= 1400px"))


def podcast_slug_validator(value: str):
    VERBOTEN = ["sw.js", "episode", "workbox-4723e66c.js", "post"]
    if value.lower() in VERBOTEN:
        raise ValidationError(_("'{value}' is a forbidden slug for podcasts.") % {"value": value})
