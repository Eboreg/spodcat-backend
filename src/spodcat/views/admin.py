import os

from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST


@login_required
@require_POST
def markdown_image_upload(request: HttpRequest):
    image = request.FILES.get("markdown-image-upload")

    if image:
        path = os.path.join("uploads", image.name)
        new_path = default_storage.save(path, image)
        return JsonResponse({
            "status": 200,
            "link": default_storage.url(new_path),
            "name": new_path.split("/")[-1],
        })

    return HttpResponse(_("Invalid request"))
