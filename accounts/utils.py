from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.http import url_has_allowed_host_and_scheme

NAME_MAX_LENGTH = 50
EMAIL_MAX_LENGTH = 254
PIN_CODE_MAX_LENGTH = 6


class ProfileValidationError(ValueError):
    pass


def clean_name(value, label):
    value = (value or "").strip()
    if len(value) > NAME_MAX_LENGTH:
        raise ProfileValidationError(f"{label} cannot exceed {NAME_MAX_LENGTH} characters.")
    return value


def clean_email(value):
    value = (value or "").strip()
    if not value:
        return ""
    if len(value) > EMAIL_MAX_LENGTH:
        raise ProfileValidationError(f"Email cannot exceed {EMAIL_MAX_LENGTH} characters.")
    try:
        validate_email(value)
    except ValidationError:
        raise ProfileValidationError("Enter a valid email address.")
    return value


def clean_pin_code(value):
    value = (value or "").strip()
    if len(value) > PIN_CODE_MAX_LENGTH:
        raise ProfileValidationError(
            f"Pin code cannot exceed {PIN_CODE_MAX_LENGTH} characters."
        )
    return value


def safe_redirect_url(request, candidate, fallback):
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return fallback