import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

MSG91_URL = "https://api.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/"


def _post_template(template_name, to, components):
    if not settings.MSG91_AUTH_KEY or not settings.MSG91_INTEGRATED_NUMBER:
        logger.error("MSG91 credentials are not configured; skipping template %s", template_name)
        return False

    payload = {
        "integrated_number": settings.MSG91_INTEGRATED_NUMBER,
        "content_type": "template",
        "payload": {
            "messaging_product": "whatsapp",
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en", "policy": "deterministic"},
                "namespace": settings.MSG91_NAMESPACE,
                "to_and_components": [{"to": to, "components": components}],
            },
        },
    }
    headers = {
        "Content-Type": "application/json",
        "authkey": settings.MSG91_AUTH_KEY,
    }

    try:
        response = requests.post(
            MSG91_URL,
            headers=headers,
            json=payload,
            timeout=settings.MSG91_TIMEOUT,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        logger.error(
            "MSG91 rejected template %s: %s %s",
            template_name,
            exc.response.status_code,
            exc.response.text,
        )
        return False
    except requests.RequestException:
        logger.exception("MSG91 request failed for template %s", template_name)
        return False
    return True


def send_otp_message(phone, otp):
    if settings.DEBUG and settings.OTP_CONSOLE_FALLBACK:
        logger.warning("DEV OTP for %s: %s (not sent, console fallback enabled)", phone, otp)
        return True

    components = {
        "body_1": {"type": "text", "value": str(otp)},
        "button_1": {"subtype": "url", "type": "text", "value": str(otp)},
    }
    return _post_template(settings.MSG91_TEMPLATE_OTP, f"91{phone}", components)


def send_pickup_details(phone, pickup_boy_name, pickup_boy_phone):
    components = {
        "body_1": {"type": "text", "value": pickup_boy_name},
        "body_2": {"type": "text", "value": pickup_boy_phone},
    }
    return _post_template(settings.MSG91_TEMPLATE_PICKUP, f"91{phone}", components)


def send_request_received(phone):
    return _post_template(settings.MSG91_TEMPLATE_RECEIVED, [f"91{phone}"], {})