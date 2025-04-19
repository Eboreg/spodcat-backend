from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from model_mixin import ModelMixin


class Artist(ModelMixin, models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["name"], name="podcasts__artist__name__uq")]
        indexes = [models.Index(fields=["name"])]
        ordering = [Lower("name")]

    def __str__(self):
        return self.name

    def has_change_permission(self, request):
        from podcasts.models import Podcast

        return request.user.is_superuser or not (
            Podcast.objects
            .filter(contents__episode__songs__artists=self)
            .exclude(Q(authors=request.user) | Q(owner=request.user))
            .exists()
        )
