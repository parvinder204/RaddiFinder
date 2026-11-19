from datetime import timedelta
from pathlib import Path

import environ
import sentry_sdk
from django.core.exceptions import ImproperlyConfigured
from sentry_sdk.integrations.django import DjangoIntegration

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)

INSECURE_SECRET_KEYS = {"", "change-me", "changeme", "secret"}
MIN_SECRET_KEY_LENGTH = 32
if not DEBUG and (
    SECRET_KEY.strip().lower() in INSECURE_SECRET_KEYS or len(SECRET_KEY) < MIN_SECRET_KEY_LENGTH
):
    raise ImproperlyConfigured(
        f"SECRET_KEY must be a unique value of at least {MIN_SECRET_KEY_LENGTH} characters when DEBUG is off."
    )
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
FDOMAIN = env("FDOMAIN", default="").rstrip("/")
USE_HTTPS = env.bool("USE_HTTPS", default=False)
API_DOCS_ENABLED = env.bool("API_DOCS_ENABLED", default=DEBUG)
CLIENT_IP_HEADER = env("CLIENT_IP_HEADER", default="")

# True when the site is only reachable from this machine (local development).
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]", "::1"}
LOCAL_ONLY = set(ALLOWED_HOSTS) <= LOCAL_HOSTS

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "common_models",
    "site_admin",
    "notifications",
    "customer_api",
    "customer_app",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_yasg",
    "django_crontab",
    "import_export",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "accounts.middleware.SessionTimeoutMiddleware",
    "accounts.middleware.NoStoreMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "RaddiFinder.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.session_sync",
                "customer_app.context_processors.total_sales",
                "customer_app.context_processors.notif_count",
                "customer_app.context_processors.notif_list",
                "customer_app.context_processors.avail_cities",
            ],
            "libraries": {
                "staticfiles": "django.templatetags.static",
            },
        },
    },
]

WSGI_APPLICATION = "RaddiFinder.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRESQLDATABASE"),
        "USER": env("POSTGRESQLUSER"),
        "PASSWORD": env("POSTGRESQLPASSWORD"),
        "HOST": env("POSTGRESQLHOST", default="localhost"),
        "PORT": env("POSTGRESQLPORT", default="5432"),
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
    }
}

CACHES = {"default": env.cache("CACHE_URL", default="locmemcache://")}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"},
    },
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = env("STATIC_ROOT", default="/var/www/RaddiFinder/static")
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# runserver only serves /static/ and /media/ itself while DEBUG is on. WhiteNoise serves
# static files with DEBUG off. Locally it reads straight from the app/static folders, so
# collectstatic is not needed; in production keep running collectstatic (nginx can still
# serve /static/ and /media/ directly and take priority).
WHITENOISE_USE_FINDERS = env.bool("WHITENOISE_USE_FINDERS", default=DEBUG or LOCAL_ONLY)
WHITENOISE_AUTOREFRESH = env.bool("WHITENOISE_AUTOREFRESH", default=DEBUG or LOCAL_ONLY)
# Uploaded media (item and profile images) with DEBUG off. On by default for local hosts
# only; production should serve MEDIA_ROOT from the web server instead.
SERVE_MEDIA = env.bool("SERVE_MEDIA", default=DEBUG or LOCAL_ONLY)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.Person"

AUTHENTICATION_BACKENDS = [
    "accounts.backends.CustomPhoneEmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]

CRONJOBS = [
    ("0 */3 * * *", "customer_app.cron.delete_old_otps"),
]

SESSION_IDLE_TIMEOUT_SECONDS = env.int("SESSION_IDLE_TIMEOUT_SECONDS", default=1800)
SESSION_ABSOLUTE_TIMEOUT_SECONDS = env.int("SESSION_ABSOLUTE_TIMEOUT_SECONDS", default=43200)
SESSION_POLL_INTERVAL_SECONDS = env.int("SESSION_POLL_INTERVAL_SECONDS", default=30)
SESSION_COOKIE_AGE = SESSION_ABSOLUTE_TIMEOUT_SECONDS
SESSION_EXPIRE_AT_BROWSER_CLOSE = env.bool("SESSION_EXPIRE_AT_BROWSER_CLOSE", default=True)
SESSION_COOKIE_SECURE = USE_HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = USE_HTTPS
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=5)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=1)),
    "UPDATE_LAST_LOGIN": False,
}
SECURE_SSL_REDIRECT = env.bool("SSL_REDIRECT", default=False)
SECURE_HSTS_SECONDS = env.int("HSTS_SECONDS", default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("HSTS_INCLUDE_SUBDOMAINS", default=False)
if env.bool("TRUST_PROXY_SSL_HEADER", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

BACKGROUND_WORKERS = env.int("BACKGROUND_WORKERS", default=4)
PICKUP_MIN_LEAD_DAYS = env.int("PICKUP_MIN_LEAD_DAYS", default=1)

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default=(
        "django.core.mail.backends.console.EmailBackend"
        if DEBUG
        else "django.core.mail.backends.smtp.EmailBackend"
    ),
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER)
SERVER_EMAIL = env("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
ADMIN_NOTIFICATION_EMAILS = env.list("ADMIN_NOTIFICATION_EMAILS", default=[])

MSG91_AUTH_KEY = env("MSG91_AUTH_KEY", default="")
MSG91_INTEGRATED_NUMBER = env("MSG91_INTEGRATED_NUMBER", default="")
MSG91_NAMESPACE = env("MSG91_NAMESPACE", default="")
MSG91_TEMPLATE_OTP = env("MSG91_TEMPLATE_OTP", default="raddi_finder")
MSG91_TEMPLATE_PICKUP = env("MSG91_TEMPLATE_PICKUP", default="pickup_detail")
MSG91_TEMPLATE_RECEIVED = env("MSG91_TEMPLATE_RECEIVED", default="received_raddifinder")
MSG91_TIMEOUT = env.int("MSG91_TIMEOUT", default=10)
MSG91_RECEIVED_USES_REFERENCE = env.bool("MSG91_RECEIVED_USES_REFERENCE", default=False)
MSG91_PICKUP_USES_REFERENCE = env.bool("MSG91_PICKUP_USES_REFERENCE", default=False)
# Local development only: print OTPs in the server console instead of sending them.
# Ignored unless DEBUG is True.
OTP_CONSOLE_FALLBACK = env.bool("OTP_CONSOLE_FALLBACK", default=False)

OTP_LENGTH = env.int("OTP_LENGTH", default=5)
OTP_EXPIRY_MINUTES = env.int("OTP_EXPIRY_MINUTES", default=180)
OTP_MAX_ATTEMPTS = env.int("OTP_MAX_ATTEMPTS", default=5)
OTP_RESEND_COOLDOWN_SECONDS = env.int("OTP_RESEND_COOLDOWN_SECONDS", default=60)
OTP_SEND_LIMIT = env.int("OTP_SEND_LIMIT", default=10)
OTP_VERIFY_LIMIT = env.int("OTP_VERIFY_LIMIT", default=30)
OTP_RATE_WINDOW_SECONDS = env.int("OTP_RATE_WINDOW_SECONDS", default=600)

SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
        send_default_pii=env.bool("SENTRY_SEND_PII", default=False),
    )

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL", default="INFO"),
    },
}

IMPORT_EXPORT_USE_TRANSACTIONS = True