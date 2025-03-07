from django.db import models
from django.db.models.functions import Lower


class Artist(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = [Lower("name")]
        constraints = [models.UniqueConstraint(fields=["name"], name="podcasts__artist__name__uq")]
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return self.name
