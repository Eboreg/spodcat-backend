from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from django import forms
from django.core.exceptions import ValidationError
from django.db import models

from spodcat import form_fields


if TYPE_CHECKING:
    from django.db.models.fields import _ChoicesList
    from django.forms.fields import _CoerceCallable
    from django.utils.choices import _ChoicesInput


class MultipleChoiceField(models.JSONField):
    choices: _ChoicesList

    def __init__(self, choices: _ChoicesInput, coerce: _CoerceCallable = str, **kwargs):
        self.coerce = coerce
        super().__init__(choices=choices, **kwargs)

    def formfield(self, **kwargs):
        return super().formfield(
            **{"choices_form_class": forms.TypedMultipleChoiceField, "coerce": self.coerce, **kwargs}
        )

    def get_choices(self, **kwargs):
        kwargs["include_blank"] = False
        return super().get_choices(**kwargs)

    def validate(self, value: Any, model_instance: models.Model | None) -> None:
        if value is None and not self.null:
            raise ValidationError(self.error_messages["null"], code="null")

        if not self.blank and value in self.empty_values:
            raise ValidationError(self.error_messages["blank"], code="blank")

        if not isinstance(value, (list, tuple)):
            raise ValidationError(
                self.error_messages["invalid"],
                code="invalid",
                params={"value": value},
            )

        if self.editable:
            if not self.blank and not value:
                raise ValidationError(self.error_messages["blank"], code="blank")

            valid_choices = []

            for option_key, option_value in self.choices:
                if isinstance(option_value, (list, tuple)):
                    for optgroup_key, _ in option_value:
                        valid_choices.append(optgroup_key)
                else:
                    valid_choices.append(option_key)

            for item in value:
                if item not in valid_choices:
                    raise ValidationError(
                        self.error_messages["invalid_choice"],
                        code="invalid_choice",
                        params={"value": item},
                    )

        try:
            json.dumps(value, cls=self.encoder)
        except TypeError:
            raise ValidationError(
                self.error_messages["invalid"],
                code="invalid",
                params={"value": value},
            ) from None


class TimestampField(models.IntegerField):
    def formfield(self, **kwargs):
        return super().formfield(**{"form_class": form_fields.TimestampField, **kwargs})
