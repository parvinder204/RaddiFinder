from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .roles import ADMIN_ROLES, expand_roles


class RestrictUserMixin(LoginRequiredMixin, UserPassesTestMixin):
    role_name = None

    def get_role_name(self):
        return self.role_name

    def test_func(self):
        role = getattr(self.request.user, "role", None)
        return role in expand_roles((self.get_role_name(),))

    def handle_no_permission(self):
        user = self.request.user
        if not user.is_authenticated:
            return redirect_to_login(
                self.request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )
        if user.role == "Customer":
            return redirect("customer:select-items")
        if user.role in ADMIN_ROLES:
            return redirect("site_admin:login")
        raise PermissionDenied
