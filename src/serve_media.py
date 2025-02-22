import mimetypes
import posixpath
import re
from io import BytesIO
from pathlib import Path

from django.http import FileResponse
from django.utils._os import safe_join
from django.views.static import serve


def serve_media(request, path, document_root=None, show_indexes=False):
    path = posixpath.normpath(path).lstrip("/")
    fullpath = Path(safe_join(document_root, path))
    file_size = fullpath.stat().st_size
    m = re.match(r"^bytes=(\d*)-(\d*)$", request.headers.get("Range", ""))

    if m:
        range_start = int(m.group(1)) if m.group(1) else 0
        range_end = int(m.group(2)) if m.group(2) else file_size
        print(f"range_start={range_start}, range_end={range_end}")
        with fullpath.open("rb") as f:
            f.seek(range_start)
            buf = BytesIO(f.read(range_end - range_start))
        content_type, encoding = mimetypes.guess_type(str(fullpath))
        response = FileResponse(buf, content_type=content_type, status=206)
        if encoding:
            response.headers["Content-Encoding"] = encoding
        response["Content-Range"] = f"bytes {range_start}-{range_end}/{file_size}"
        response["Content-Length"] = range_end - range_start
    else:
        response = serve(request, path, document_root, show_indexes)
        response["Content-Length"] = file_size

    response["Accept-Ranges"] = "bytes"
    return response
