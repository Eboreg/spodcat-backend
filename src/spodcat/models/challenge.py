import random
import uuid
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.utils import translation
from django.utils.translation import gettext_lazy as _

from spodcat.model_mixin import ModelMixin


if TYPE_CHECKING:
    from spodcat.models import Podcast


def generate_term():
    return random.randint(1, 9)


class Challenge(ModelMixin, models.Model):
    NUMBER_STRINGS = [
        _("zero"),
        _("one"),
        _("two"),
        _("three"),
        _("four"),
        _("five"),
        _("six"),
        _("seven"),
        _("eight"),
        _("nine"),
    ]

    created = models.DateTimeField(auto_now_add=True)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    term1 = models.PositiveSmallIntegerField(default=generate_term)
    term2 = models.PositiveSmallIntegerField(default=generate_term)
    podcast: "Podcast" = models.ForeignKey("spodcat.Podcast", on_delete=models.CASCADE, related_name="+")

    class Meta:
        verbose_name = _("challenge")
        verbose_name_plural = _("challenges")

    @property
    # pylint: disable=no-member,invalid-sequence-index
    def challenge_string(self):
        with translation.override(self.podcast.language or settings.LANGUAGE_CODE):
            return _("%(term1)s plus %(term2)s") % {
                "term1": self.NUMBER_STRINGS[self.term1],
                "term2": self.NUMBER_STRINGS[self.term2],
            }
