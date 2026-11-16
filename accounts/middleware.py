import time

from django.conf import settings
from django.contrib.auth import logout
from django.urls import reverse
from django.utils.cache import add_never_cache_headers

LAST_ACTIVITY_KEY = "last_activity"
STARTED_KEY = "session_started"
ACTIVITY_WRITE_INTERVAL_SECONDS = 30


class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            self._enforce(request)
        return self.get_response(request)

    def _enforce(self, request):
        now = time.time()
        session = request.session
        last_activity = session.get(LAST_ACTIVITY_KEY)
        started = session.get(STARTED_KEY)

        idle_expired = (
            last_activity is not None
            and now - last_activity > settings.SESSION_IDLE_TIMEOUT_SECONDS
        )
        absolute_expired = (
            started is not None and now - started > settings.SESSION_ABSOLUTE_TIMEOUT_SECONDS
        )
        if idle_expired or absolute_expired:
            logout(request)
            return

        if started is None:
            session[STARTED_KEY] = now
        due = last_activity is None or now - last_activity >= ACTIVITY_WRITE_INTERVAL_SECONDS
        if due and self._counts_as_activity(request):
            session[LAST_ACTIVITY_KEY] = now

    def _counts_as_activity(self, request):
        if request.path != reverse("accounts:session-status"):
            return True
        return request.GET.get("active") == "1"


class NoStoreMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            add_never_cache_headers(response)
        return response
