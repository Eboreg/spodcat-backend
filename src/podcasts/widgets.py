from django import forms
from django.conf import settings
from django.contrib.admin.widgets import AutocompleteSelectMultiple
from django.core.validators import EMPTY_VALUES


class ArtistAutocompleteWidget(AutocompleteSelectMultiple):
    @property
    def media(self):
        extra = "" if settings.DEBUG else ".min"

        return forms.Media(
            js=(
                f"admin/js/vendor/jquery/jquery{extra}.js",
                f"admin/js/vendor/select2/select2.full{extra}.js",
                "admin/js/jquery.init.js",
                "spodcat/js/artist_autocomplete.js",
            ),
            css={
                "screen": (
                    f"admin/css/vendor/select2/select2{extra}.css",
                    "admin/css/autocomplete.css",
                ),
            },
        )

    def optgroups(self, name, value, attr=None):
        selected_choices = {str(v) for v in value if str(v) not in EMPTY_VALUES}
        subgroup = []
        for idx, artist in enumerate([a for a in self.choices if str(a.id) in value]):
            subgroup.append(self.create_option(name, artist.id, artist.name, selected_choices, idx))
        return [(None, subgroup, 0)]
