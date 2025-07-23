import re

from django.apps import apps
from django.core.exceptions import ValidationError
from django.forms import CharField, ModelChoiceField, ModelForm, Select
from django.utils.translation import gettext as _

from spodcat.models import FontFace, Podcast, PodcastContent
from spodcat.models.video import Video


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


class PodcastContentVideoAdminForm(ModelForm):
    url_or_id = CharField(max_length=200)

    class Meta:
        fields = ["video_type", "url_or_id", "title"]
        model = Video

    def __init__(self, data=None, instance: Video | None = None, **kwargs):
        super().__init__(data, instance=instance, **kwargs)
        if instance:
            self.fields["url_or_id"].initial = instance.video_id

    def clean(self):
        if not self.cleaned_data["DELETE"]:
            url_or_id: str = self.cleaned_data["url_or_id"]

            if not url_or_id.startswith("http"):
                self.cleaned_data["video_id"] = url_or_id
            else:
                patt1 = r"(?:www\.)?youtube\.com\/watch[^<>\s]*[&?]v=([^&<>\s]*)[^<>\s]*"
                patt2 = r"youtu\.be\/([^?&<>\s]*)[^<>\s]*"
                patt = rf"^(https:\/\/(?:(?:{patt1})|(?:{patt2})))(.*)$"
                match = re.search(patt, url_or_id)

                if match:
                    self.cleaned_data["video_id"] = match.group(2) or match.group(3)
                else:
                    raise ValidationError({"url_or_id": _("Invalid video ID or URL.")})

        return self.cleaned_data

    def save(self, commit: bool = True):
        self.instance.video_id = self.cleaned_data["video_id"]
        return super().save(commit)
