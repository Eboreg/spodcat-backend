from django import forms
from django.conf import settings
from django.contrib.admin.widgets import (
    AdminTextareaWidget,
    AutocompleteSelectMultiple,
)
from django.core.validators import EMPTY_VALUES
from django.forms import Widget
from martor.widgets import MartorWidget as BaseMartorWidget


class MartorWidget(BaseMartorWidget):
    class Media:
        css = {
            "all": (
                "plugins/css/bootstrap.min.css",
                "martor/css/martor-admin.min.css",
                "plugins/css/ace.min.css",
                "plugins/css/resizable.min.css",
                "spodcat/css/martor.css",
            )
        }

        extend = False

        js = (
            "plugins/js/jquery.min.js",
            "plugins/js/bootstrap.min.js",
            "plugins/js/ace.js",
            "plugins/js/mode-markdown.js",
            "plugins/js/ext-language_tools.js",
            "plugins/js/theme-github.js",
            "plugins/js/highlight.min.js",
            "plugins/js/resizable.min.js",
            "plugins/js/emojis.min.js",
            "martor/js/martor.bootstrap.min.js",
        )


class AdminMartorWidget(MartorWidget, AdminTextareaWidget):
    pass


class ReadOnlyInlineModelWidget(Widget):
    read_only = True
    template_name = "admin/readonly_inline_model.html"

    def get_instance_dict(self, instance):
        return {}

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["instance"] = self.get_instance_dict(value) if value else None
        return context


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
