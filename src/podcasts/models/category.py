from html import escape

from django.db import models


class Category(models.Model):
    cat = models.CharField(max_length=50)
    sub = models.CharField(max_length=50, null=True, default=None)

    class Meta:
        ordering = ["cat", "sub"]
        indexes = [models.Index(fields=["cat", "sub"])]

    def __str__(self):
        if self.sub:
            return f"{self.cat} / {self.sub}"
        return self.cat

    def to_dict(self):
        if self.sub:
            return {"cat": escape(self.cat), "sub": escape(self.sub)}
        return {"cat": escape(self.cat)}
