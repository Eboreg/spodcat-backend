from django.apps import AppConfig


class PodcastsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'podcasts'

    def ready(self):
        from podcasts import signals
