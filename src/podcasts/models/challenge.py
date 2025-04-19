import random
import uuid

from django.db import models

from model_mixin import ModelMixin


def generate_term():
    return random.randint(1, 9)


class Challenge(ModelMixin, models.Model):
    NUMBER_STRINGS = ["noll", "ett", "två", "tre", "fyra", "fem", "sex", "sju", "åtta", "nio"]

    created = models.DateTimeField(auto_now_add=True)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    term1 = models.PositiveSmallIntegerField(default=generate_term)
    term2 = models.PositiveSmallIntegerField(default=generate_term)

    @property
    def challenge_string(self):
        # pylint: disable=invalid-sequence-index
        return f"{self.NUMBER_STRINGS[self.term1]} plus {self.NUMBER_STRINGS[self.term2]}"
