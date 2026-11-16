from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from accounts.roles import ADMIN_ROLES, logout_route
from accounts.utils import safe_redirect_url

CLEAR_SITE_DATA = '"cache", "cookies", "storage"'


class LoginView(View):
    def post(self, request):
        identifier = request.POST.get("email", "").strip() or request.session.get("phone", "")
        password = request.POST.get("password", "")

        user = authenticate(request, email=identifier, phone=identifier, password=password)
        if user is None:
            messages.error(request, "Invalid Credentials. Try again.", extra_tags="unauthorised")
            return redirect(
                safe_redirect_url(
                    request,
                    request.META.get("HTTP_REFERER"),
                    reverse("customer:phone-number"),
                )
            )

        fallback = reverse(
            "site_admin:dashboard" if user.role in ADMIN_ROLES else "customer:select-items"
        )
        next_url = safe_redirect_url(request, request.session.get("next"), fallback)

        request.session.pop("phone", None)
        login(request, user)
        return redirect(next_url)


@never_cache
@require_GET
def session_status(request):
    return JsonResponse({"authenticated": request.user.is_authenticated})


@never_cache
@require_http_methods(["GET", "POST"])
def logout_view(request):
    post_logout_url = reverse(logout_route(request.user))
    logout(request)

    response = render(
        request,
        "accounts/logged_out.html",
        {
            "session_sync_config": {
                "mode": "logout",
                "authenticated": False,
                "postLogoutUrl": post_logout_url,
            }
        },
    )
    response["Clear-Site-Data"] = CLEAR_SITE_DATA
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    return response
