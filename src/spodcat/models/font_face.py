from django.db import models
from django.db.models.functions.text import Lower
from django.utils.translation import gettext_lazy as _

from spodcat.model_mixin import ModelMixin
from spodcat.models.functions import (
    fontface_file_storage,
    fontface_file_upload_to,
)


class FontFace(ModelMixin, models.Model):
    class Format(models.TextChoices):
        TRUETYPE = "truetype", "Truetype"
        WOFF = "woff", "WOFF 1.0"
        WOFF2 = "woff2", "WOFF 2.0"
        OPENTYPE = "opentype", "Opentype"
        COLLECTION = "collection", "Opentype Collection"
        EMBEDDED_OPENTYPE = "embedded-opentype", "Embedded Opentype"
        SVG = "svg", "SVG font (deprecated)"

    name = models.CharField(max_length=30, verbose_name=_("name"), blank=True, unique=True)
    file = models.FileField(
        upload_to=fontface_file_upload_to,
        verbose_name=_("font file"),
        storage=fontface_file_storage,
    )
    format = models.CharField(max_length=20, choices=Format.choices, verbose_name=_("format"), null=True, default=None)
    weight = models.PositiveSmallIntegerField(
        verbose_name=_("weight"),
        choices=[(c, str(c)) for c in range(100, 901, 100)],
        default=400,
    )
    updated = models.DateTimeField()

    class Meta:
        verbose_name = _("font face")
        verbose_name_plural = _("font faces")
        ordering = [Lower("name")]

    def __str__(self):
        return f"{self.name} ({self.weight})"

    @classmethod
    def guess_format(cls, filename: str, content_type: str) -> Format | None:
        filename = filename.lower()

        if content_type in ("font/ttf", "application/x-font-ttf") or filename.endswith(".ttf"):
            return cls.Format.TRUETYPE
        if content_type == "font/woff" or filename.endswith(".woff"):
            return cls.Format.WOFF
        if content_type == "font/woff2" or filename.endswith(".woff2"):
            return cls.Format.WOFF2
        if content_type == "image/svg+xml" or filename.endswith(".svg"):
            return cls.Format.SVG
        if content_type in ("font/otf", "application/x-font-otf") or filename.endswith(".otf"):
            return cls.Format.OPENTYPE
        if content_type == "application/vnd.ms-fontobject" or filename.endswith(".eot"):
            return cls.Format.EMBEDDED_OPENTYPE
        if content_type == "font/collection" or filename.endswith("ttc"):
            return cls.Format.COLLECTION

        return None

    # pylint: disable=no-member,bad-string-format-type
    def get_css(self):
        format_str = f" format({self.format})" if self.format else ""
        rules = [
            f'font-family: "{self.name}";',
            f'src: url("{self.file.url}"){format_str};',
            f"font-weight: {self.weight};",
        ]

        return "@font-face {" + " ".join(rules) + "}"
