from html import escape

from django.db import models
from django.utils.translation import gettext_lazy as _

from spodcat.data import CATEGORIES

from .model_mixin import ModelMixin


class Category(ModelMixin, models.Model):
    cat = models.CharField(max_length=50)
    sub = models.CharField(max_length=50, null=True, default=None)

    class Meta:
        ordering = ["cat", "sub"]
        indexes = [models.Index(fields=["cat", "sub"])]
        verbose_name = _("category")
        verbose_name_plural = _("categories")

    def __str__(self):
        if self.sub:
            return f"{self.cat} / {self.sub}"
        return self.cat

    @classmethod
    def bootstrap(cls):
        categories = list(cls.objects.all())
        new_categories = []

        def conditional_append(cat: str, sub: str | None):
            if len([c for c in categories if c.cat == cat and c.sub == sub]) == 0:
                new_categories.append(cls(cat=cat, sub=sub))

        for cat, subs in CATEGORIES.items():
            conditional_append(cat=cat, sub=None)
            for sub in subs:
                conditional_append(cat=cat, sub=sub)

        if new_categories:
            cls.objects.bulk_create(new_categories)

    def to_dict(self):
        if self.sub:
            return {"cat": escape(self.cat), "sub": escape(self.sub)}
        return {"cat": escape(self.cat)}
