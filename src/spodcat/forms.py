from django.apps import apps
from django.core.exceptions import ValidationError
from django.forms import ModelChoiceField, ModelForm, Select
from django.utils.translation import gettext as _

from spodcat.models import FontFace, Podcast, PodcastContent


class PodcastChangeSlugForm(ModelForm):
    class Meta:
        fields = ["slug"]
        model = Podcast

    def clean_slug(self):
        slug = self.cleaned_data["slug"]

        if self.has_changed() and Podcast.objects.filter(slug=slug).exists():
            raise ValidationError(_("Another podcast with slug=%(slug)s exists.") % {"slug": slug})

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
            PodcastContent.objects.filter(podcast=old_instance).update(podcast=self.instance)

            if apps.is_installed("spodcat.logs"):
                from spodcat.logs.models import (
                    PodcastRequestLog,
                    PodcastRssRequestLog,
                )

                PodcastRequestLog.objects.filter(podcast=old_instance).update(podcast=self.instance)
                PodcastRssRequestLog.objects.filter(podcast=old_instance).update(podcast=self.instance)

            old_instance.delete()

        return self.instance


class FontFaceSelect(Select):
    template_name = "spodcat/font_face_select.html"


class PodcastAdminForm(ModelForm):
    name_font_face = ModelChoiceField(queryset=FontFace.objects.all(), widget=FontFaceSelect)
