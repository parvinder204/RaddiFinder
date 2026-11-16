ADMIN_ROLES = ("Admin", "SuperUser")

LOGOUT_ROUTES = {
    "Customer": "customer:select-items",
    "Admin": "site_admin:login",
    "SuperUser": "site_admin:login",
}
DEFAULT_LOGOUT_ROUTE = "customer:select-items"


def expand_roles(roles):
    expanded = set(roles)
    if "Admin" in expanded:
        expanded.update(ADMIN_ROLES)
    return tuple(expanded)


def logout_route(user):
    return LOGOUT_ROUTES.get(getattr(user, "role", None), DEFAULT_LOGOUT_ROUTE)
