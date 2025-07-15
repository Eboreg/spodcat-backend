import mimetypes
import posixpath
from io import BytesIO
from pathlib import Path

from django.http import FileResponse, HttpResponseNotFound
from django.utils._os import safe_join
from django.views.static import serve

from spodcat.utils import (
    extract_range_request_header,
    set_range_response_headers,
)


def serve_media(request, path, document_root=None, show_indexes=False):
    path = posixpath.normpath(path).lstrip("/")
    fullpath = Path(safe_join(document_root, path)) if document_root else Path(path)

    if not fullpath.is_file():
        return HttpResponseNotFound()

    file_size = fullpath.stat().st_size
    range_header = extract_range_request_header(request)

    if range_header:
        range_start, range_end = range_header

        with fullpath.open("rb") as f:
            f.seek(range_start)
            buf = BytesIO(f.read(range_end - range_start))

        content_type, encoding = mimetypes.guess_type(str(fullpath))
        response = FileResponse(buf, content_type=content_type, status=206)

        if encoding:
            response.headers["Content-Encoding"] = encoding

        set_range_response_headers(response, range_start, range_end, file_size)
    else:
        response = serve(request, path, document_root, show_indexes)
        response["Content-Length"] = file_size

    response["Accept-Ranges"] = "bytes"
    return response
