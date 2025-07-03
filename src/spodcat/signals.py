from django.db.models.signals import pre_delete
from django.dispatch import receiver

from spodcat.models import Episode, FontFace, Podcast
from spodcat.utils import delete_storage_file


@receiver(pre_delete, sender=Episode, dispatch_uid="on_episode_pre_delete")
def on_episode_pre_delete(sender, instance: Episode, **kwargs):
    delete_storage_file(instance.audio_file)
    delete_storage_file(instance.image)
    delete_storage_file(instance.image_thumbnail)


@receiver(pre_delete, sender=Podcast, dispatch_uid="on_podcast_pre_delete")
def on_podcast_pre_delete(sender, instance: Podcast, **kwargs):
    delete_storage_file(instance.banner)
    delete_storage_file(instance.cover)
    delete_storage_file(instance.favicon)
    delete_storage_file(instance.cover_thumbnail)


@receiver(pre_delete, sender=FontFace, dispatch_uid="on_fontface_pre_delete")
def on_fontface_pre_delete(sender, instance: FontFace, **kwargs):
    delete_storage_file(instance.file)
