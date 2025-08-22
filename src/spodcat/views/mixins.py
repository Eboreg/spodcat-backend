import logging
from typing import TYPE_CHECKING, Iterable

from rest_framework.request import Request
from rest_framework_json_api.views import (
    PreloadIncludesMixin as BasePreloadIncludesMixin,
)


if TYPE_CHECKING:
    from spodcat.logs.models import RequestLog


logger = logging.getLogger(__name__)


class LogRequestMixin:
    def log_request(self, request: Request, log_class: type["RequestLog"], **kwargs):
        try:
            log_class.create_from_request(request, **kwargs)
        except Exception as e:
            logger.error("Could not create %s: %s", log_class.__name__, e, exc_info=e)


class PreloadIncludesMixin(BasePreloadIncludesMixin):
    """
    Tweaked version that also returns the selects/prefetches for all "parents".
    I.e. for "include=podcast.categories", prefetch_for_includes["podcast"]
    and prefetch_for_includes["podcast.categories"] will be combined.
    """
    def _get_x_related(self, include: str, propname: str):
        # "x" = prefetch or select
        x_for_includes: dict[str, Iterable] = getattr(self, propname, {})
        xs = list(x_for_includes.get(include, []))
        while "." in include:
            include = include.rsplit(".", maxsplit=1)[0]
            xs.extend(list(x_for_includes.get(include, [])))
        return xs or None

    def get_prefetch_related(self, include: str):
        return self._get_x_related(include, "prefetch_for_includes")

    def get_select_related(self, include: str):
        return self._get_x_related(include, "select_for_includes")
