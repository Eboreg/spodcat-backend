import random
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.model_mixin import ModelMixin


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

    @property
    def challenge_string(self):
        # pylint: disable=invalid-sequence-index
        return _("%(term1)s plus %(term2)s") % {
            "term1": self.NUMBER_STRINGS[self.term1],
            "term2": self.NUMBER_STRINGS[self.term2],
        }
