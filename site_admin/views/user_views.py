from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET

from accounts.utils import safe_redirect_url


@require_GET
def site_admin_login(request):
    default = reverse("site_admin:dashboard")
    request.session["next"] = safe_redirect_url(request, request.GET.get("next"), default)
    return render(request, "site_admin/login.html")
