from django.contrib.admin.widgets import AdminTextareaWidget
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
                "assets/css/martor.css",
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
