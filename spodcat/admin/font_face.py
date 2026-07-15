import random

from django.contrib import admin
from django.core.files.uploadedfile import UploadedFile
from django.db import models
from django.forms import ClearableFileInput, ModelForm
from django.http import HttpRequest
from django.utils.timezone import now

from spodcat.contrib.admin.mixin import AdminMixin
from spodcat.models import FontFace
from spodcat.utils import delete_storage_file


class FontFileWidget(ClearableFileInput):
    def build_attrs(self, base_attrs: dict, extra_attrs: dict | None = None):
        return {
            **super().build_attrs(base_attrs, extra_attrs),
            "accept": ".woff, .woff2, .ttf, .otf, .eot, .svg, .svgz, .otc, .ttc, font/*",
        }


class FontFaceAdmin(AdminMixin, admin.ModelAdmin):
    list_display = ["name", "format", "weight"]
    formfield_overrides = {
        models.FileField: {"widget": FontFileWidget},
    }
    add_fields = ["name", "file", "weight"]
    fields = ["name", "file", "format", "weight"]
    sample_texts = [
        "Umpo bumpo español",
        "Stora, smidiga sedlar",
        "Slå smutsen in i mig",
        "Doftar det autistbarn här?",
        "You touch my tra-la-la",
        "Tro på Gud och runka pung",
        "Triangel",
        "Homosexualitet",
    ]

    def change_view(self, request: HttpRequest, object_id, form_url="", extra_context: dict | None = None):
        extra_context = extra_context or {}
        extra_context["sample_text"] = random.choice(self.sample_texts)
        return super().change_view(request, object_id, form_url, extra_context)

    def get_fields(self, request: HttpRequest, obj: FontFace | None = None):
        if obj:
            return self.fields
        return self.add_fields

    def save_form(self, request: HttpRequest, form: ModelForm, change: bool):
        instance: FontFace = super().save_form(request, form, change)

        if not change or form.has_changed():
            instance.updated = now()

        if ("name" in form.changed_data or not change) and instance.file.name and not instance.name.strip():
            instance.name = instance.file.name.split("/")[-1].split(".")[0][:30]

        if "file" in form.changed_data:
            if "file" in form.cleaned_data:
                font_file: UploadedFile = form.cleaned_data["file"]
                if font_file.content_type and font_file.name:
                    instance.format = FontFace.guess_format(font_file.name, content_type=font_file.content_type)

            if "file" in form.initial:
                delete_storage_file(form.initial["file"])

        return instance
