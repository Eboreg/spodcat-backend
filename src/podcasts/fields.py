from django import forms

from podcasts.utils import seconds_to_timestamp


class ArtistMultipleChoiceField(forms.ModelMultipleChoiceField):
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


class TimestampField(forms.Field):
    widget = forms.TimeInput

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
