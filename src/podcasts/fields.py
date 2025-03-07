from django.contrib.admin.widgets import AutocompleteSelectMultiple
from django.core.validators import EMPTY_VALUES
from django.forms import Field, ModelForm, ModelMultipleChoiceField, TimeInput


def seconds_to_timestamp(value: int):
    hours = int(value / 60 / 60)
    minutes = int(value / 60 % 60)
    seconds = int(value % 60 % 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


class ArtistAutocompleteWidget(AutocompleteSelectMultiple):
    def optgroups(self, name, value, attr=None):
        selected_choices = {str(v) for v in value if str(v) not in EMPTY_VALUES}
        subgroup = []
        for idx, artist in enumerate([a for a in self.choices if str(a.id) in value]):
            subgroup.append(self.create_option(name, artist.id, artist.name, selected_choices, idx))
        return [(None, subgroup, 0)]


class ArtistMultipleChoiceField(ModelMultipleChoiceField):
    def __init__(self, queryset, **kwargs):
        super().__init__(queryset, **kwargs)
        self._choices = list(queryset)

    def clean(self, value):
        value = self.prepare_value(value)
        new_value = []
        for pk in value:
            if isinstance(pk, str) and pk.startswith("NEW--"):
                name = pk[5:]
                artist = self.queryset.filter(name__iexact=name).first()
                if not artist:
                    artist = self.queryset.create(name=name)
                new_value.append(artist.pk)
            else:
                new_value.append(pk)
        return super().clean(new_value)


class TimestampField(Field):
    widget = TimeInput

    def prepare_value(self, value):
        if isinstance(value, int):
            return seconds_to_timestamp(value)
        return super().prepare_value(value)

    def to_python(self, value):
        if isinstance(value, str) and value:
            value = value.replace(".", ":")
            parts = value.split(":")
            seconds = int(parts[-1]) if len(parts) > 0 else 0
            minutes = int(parts[-2]) if len(parts) > 1 else 0
            hours = int(parts[-3]) if len(parts) > 2 else 0
            return seconds + (minutes * 60) + (hours * 60 * 60)
        return super().to_python(value)


class EpisodeSongForm(ModelForm):
    timestamp = TimestampField()
