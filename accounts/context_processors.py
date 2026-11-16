from django.conf import settings
from django.urls import reverse

from .roles import logout_route


def session_sync(request):
    user = request.user
    return {
        "session_sync_config": {
            "mode": "page",
            "authenticated": user.is_authenticated,
            "statusUrl": reverse("accounts:session-status"),
            "postLogoutUrl": reverse(logout_route(user)),
            "idleTimeout": settings.SESSION_IDLE_TIMEOUT_SECONDS,
            "pollInterval": settings.SESSION_POLL_INTERVAL_SECONDS,
        }
    }
