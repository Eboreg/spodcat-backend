from datetime import datetime

from django.db.models import Max
from django.http import HttpRequest, HttpResponse
from django.utils.http import http_date

from spodcat.models import FontFace


def font_face_css(request: HttpRequest):
    font_faces = FontFace.objects.all()
    last_modified_dict = FontFace.objects.values(latest=Max("updated")).first()
    last_modified: datetime | None = last_modified_dict["latest"] if last_modified_dict else None
    css = "\n".join(ff.get_css() for ff in font_faces).encode()
    headers = {
        "Content-Disposition": 'inline; filename="font-faces.css"',
        "Content-Length": len(css),
    }

    if last_modified:
        headers["Last-Modified"] = http_date(last_modified.timestamp())

    return HttpResponse(
        content=css,
        content_type="text/css; charset=utf-8",
        headers=headers,
    )
