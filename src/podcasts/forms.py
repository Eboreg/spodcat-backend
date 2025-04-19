from django.core.exceptions import ValidationError
from django.forms import ModelForm

from logs.models import PodcastRequestLog, PodcastRssRequestLog
from podcasts.fields import TimestampField
from podcasts.models import Podcast, PodcastContent


class EpisodeSongForm(ModelForm):
    timestamp = TimestampField()


class PodcastChangeSlugForm(ModelForm):
    class Meta:
        fields = ["slug"]
        model = Podcast

    def clean_slug(self):
        slug = self.cleaned_data["slug"]
        if self.has_changed() and Podcast.objects.filter(slug=slug).exists():
            raise ValidationError(f"Another podcast with slug={slug} exists.")
        return slug

    def save(self, commit=True):
        if commit and self.has_changed():
            assert isinstance(self.instance, Podcast)
            old_instance = Podcast.objects.get(slug=self.initial["slug"])
            self.instance.save()
            self.instance.refresh_from_db()
            self.instance.authors.set(old_instance.authors.all())
            self.instance.categories.set(old_instance.categories.all())
            self.instance.links.set(old_instance.links.all())
            PodcastRequestLog.objects.filter(podcast=old_instance).update(podcast=self.instance)
            PodcastRssRequestLog.objects.filter(podcast=old_instance).update(podcast=self.instance)
            PodcastContent.objects.filter(podcast=old_instance).update(podcast=self.instance)
            old_instance.delete()
        return self.instance
