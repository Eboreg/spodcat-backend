from django.db import models


class EpisodeSong(models.Model):
    artists = models.ManyToManyField("podcasts.Artist", related_name="songs", blank=True)
    comment = models.CharField(max_length=100, null=True, default=None, blank=True)
    episode = models.ForeignKey("podcasts.Episode", on_delete=models.CASCADE, related_name="songs")
    name = models.CharField(max_length=100)
    timestamp = models.PositiveIntegerField()

    class Meta:
        ordering = ["timestamp"]
        indexes = [models.Index(fields=["timestamp"])]

    def __str__(self):
        return self.name
