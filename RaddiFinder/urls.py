from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as serve_media
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from common_models.views import pickup_image
from RaddiFinder.views import devtools_probe

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("site_admin/", include("site_admin.urls", namespace="site_admin")),
    path("customer_api/", include("customer_api.urls", namespace="customer_api")),
    path("", include("customer_app.urls", namespace="customer")),
    path("utilities/", include("common_models.urls", namespace="utilities")),
    path(
        f"{settings.MEDIA_URL.strip('/')}/pickup_request/<str:filename>",
        pickup_image,
        name="pickup-image",
    ),
]

if settings.API_DOCS_ENABLED:
    schema_view = get_schema_view(
        openapi.Info(
            title="RaddiFinder API",
            default_version="v1",
            description="API documentation for RaddiFinder",
        ),
        public=True,
        permission_classes=[permissions.AllowAny],
    )
    urlpatterns += [
        path("docs/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
        path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    ]

if settings.DEBUG:
    urlpatterns += [
        path(".well-known/appspecific/com.chrome.devtools.json", devtools_probe, name="devtools-probe"),
    ]

if settings.SERVE_MEDIA and not settings.DEBUG:
    # DEBUG off: static() below adds nothing, so serve uploaded media explicitly.
    # pickup_image (registered earlier) still guards pickup_request/ files.
    urlpatterns += [
        re_path(
            rf"^{settings.MEDIA_URL.strip('/')}/(?P<path>.*)$",
            serve_media,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)