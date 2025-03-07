from django.db import models


class EpisodeSong(models.Model):
    episode = models.ForeignKey("podcasts.Episode", on_delete=models.CASCADE, related_name="songs")
    artists = models.ManyToManyField("podcasts.Artist", related_name="songs", blank=True)
    name = models.CharField(max_length=100)
    comment = models.CharField(max_length=100, null=True, default=None, blank=True)
    timestamp = models.PositiveIntegerField()

    class Meta:
        ordering = ["timestamp"]
        indexes = [models.Index(fields=["timestamp"])]

    def __str__(self):
        return self.name
