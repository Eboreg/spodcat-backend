import logging
from typing import TYPE_CHECKING

from rest_framework.request import Request


if TYPE_CHECKING:
    from spodcat.logs.models import RequestLog


logger = logging.getLogger(__name__)


class LogRequestMixin:
    def log_request(self, request: Request, log_class: type["RequestLog"], **kwargs):
        try:
            log_class.create_from_request(request, **kwargs)
        except Exception as e:
            logger.error("Could not create %s: %s", log_class.__name__, e, exc_info=e)
