from typing import Any, Mapping

from klaatu_python.utils import is_truthy
from rest_framework import renderers
from rest_framework.request import Request
from rest_framework.views import APIView


class BrowsableAPIRenderer(renderers.BrowsableAPIRenderer):
    def get_context(
        self,
        data: Any,
        accepted_media_type: str | None,
        renderer_context: Mapping[str, Any],
    ) -> dict[str, Any]:
        context = super().get_context(data, accepted_media_type, renderer_context)
        context["description"] = "Add `?forms=0` to the URL to skip the edit forms and their extra SQL overhead."

        return context

    def show_form_for_method(self, view: APIView, method: str, request: Request, obj: Any) -> bool | None:
        if "forms" in request.query_params and not is_truthy(request.query_params["forms"]):
            return False
        return super().show_form_for_method(view, method, request, obj)
