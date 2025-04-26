from django.db import models

from utils.model_mixin import ModelMixin


def podcast_link_icon_path(instance: "PodcastLink", filename: str):
    return f"{instance.podcast.slug}/images/links/{filename}"


class PodcastLink(ModelMixin, models.Model):
    class Icon(models.TextChoices):
        FACEBOOK = "facebook", "Facebook"
        PATREON = "patreon", "Patreon"
        DISCORD = "discord", "Discord"
        APPLE = "apple", "Apple"
        ANDROID = "android", "Android"
        SPOTIFY = "spotify", "Spotify"
        ITUNES = "itunes", "Itunes"

    class Theme(models.TextChoices):
        PRIMARY = "primary", "Primary"
        SECONDARY = "secondary", "Secondary"
        TERTIARY = "tertiary", "Tertiary"

    custom_icon = models.ImageField(upload_to=podcast_link_icon_path, null=True, default=None, blank=True)
    icon = models.CharField(max_length=10, choices=Icon, null=True, default=None)
    label = models.CharField(max_length=100)
    order = models.PositiveSmallIntegerField(default=0)
    podcast = models.ForeignKey("podcasts.Podcast", on_delete=models.CASCADE, related_name="links")
    theme = models.CharField(max_length=10, choices=Theme, default=Theme.PRIMARY)
    url = models.URLField()

    class Meta:
        ordering = ["order"]
        indexes = [models.Index(fields=["order"])]
