from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

from .roles import expand_roles


def role_required(*roles, login_url=None, json=False):
    allowed = expand_roles(roles)

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                if json:
                    return JsonResponse(
                        {"status": False, "notes": "Authentication required."}, status=401
                    )
                return redirect_to_login(request.get_full_path(), login_url)
            if user.role not in allowed:
                if json:
                    return JsonResponse({"status": False, "notes": "Permission denied."}, status=403)
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
