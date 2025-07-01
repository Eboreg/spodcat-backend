from django import forms


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
