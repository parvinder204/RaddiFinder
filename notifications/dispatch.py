import logging
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(
    max_workers=settings.BACKGROUND_WORKERS, thread_name_prefix="notify"
)


def _run(func, args, kwargs):
    try:
        func(*args, **kwargs)
    except Exception:
        logger.exception("Background task %s failed", getattr(func, "__name__", repr(func)))


def run_in_background(func, *args, **kwargs):
    transaction.on_commit(lambda: _executor.submit(_run, func, args, kwargs))
