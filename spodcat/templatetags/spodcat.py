import datetime

from country_list import countries_for_language
from django import template
from django.template.defaultfilters import stringfilter
from django.utils import formats
from django.utils.translation import get_language, gettext as _

from spodcat.settings import spodcat_settings


register = template.Library()


@register.filter
def month(value: dict):
    return formats.date_format(datetime.date.fromisoformat(f"{value['year']}-{value['month']}-01"), "M Y")


@register.filter
def timedelta(value):
    if isinstance(value, datetime.timedelta) and value.days > 0:
        return _("%(days)d days, %(time)s") % {
            "days": value.days,
            "time": str(datetime.timedelta(seconds=value.seconds)),
        }

    return "-" if value is None else str(value)


@register.filter
def duration_seconds(value):
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            value = None

    if isinstance(value, (int, float)):
        return timedelta(datetime.timedelta(seconds=int(value)))

    return "-" if value is None else str(value)


@register.filter
@stringfilter
def country_code(value: str):
    value = value.upper()

    try:
        countries = dict(countries_for_language(get_language()))
    except ValueError:
        countries = dict(countries_for_language("en"))

    if value in countries:
        return countries[value]

    return value


@register.simple_tag
def root_path():
    return spodcat_settings.get_backend_root_path()
