from django.conf import settings
from django.core.cache import cache
from rest_framework.throttling import BaseThrottle


def client_ip(request):
    header = settings.CLIENT_IP_HEADER
    if header:
        value = request.META.get(header, "")
        if value:
            return value.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def is_rate_limited(request, scope, limit, window):
    key = f"throttle:{scope}:{client_ip(request)}"
    if cache.add(key, 1, window):
        return False
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, window)
        return False
    return count > limit


def otp_send_limited(request):
    return is_rate_limited(
        request, "otp-send", settings.OTP_SEND_LIMIT, settings.OTP_RATE_WINDOW_SECONDS
    )


def otp_verify_limited(request):
    return is_rate_limited(
        request, "otp-verify", settings.OTP_VERIFY_LIMIT, settings.OTP_RATE_WINDOW_SECONDS
    )


class OTPSendThrottle(BaseThrottle):
    def allow_request(self, request, view):
        return not otp_send_limited(request)


class OTPVerifyThrottle(BaseThrottle):
    def allow_request(self, request, view):
        return not otp_verify_limited(request)
