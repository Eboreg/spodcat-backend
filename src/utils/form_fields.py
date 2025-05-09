from django import forms

from utils import seconds_to_timestamp


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

    def widget_attrs(self, widget):
        return {"class": "timestamp-field"}
