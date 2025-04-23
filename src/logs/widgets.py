from django.forms import Widget


class ReadOnlyInlineModelWidget(Widget):
    read_only = True
    template_name = "admin/logs/readonly_inline_model.html"

    def get_instance_dict(self, instance):
        return {}

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["instance"] = self.get_instance_dict(value) if value else None
        return context
