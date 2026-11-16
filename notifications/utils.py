import logging
from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags

from accounts.roles import ADMIN_ROLES
from common_models.models import Pickup

from .dispatch import run_in_background
from .models import Notifications, Recipients
from .sms import send_pickup_details, send_request_received

logger = logging.getLogger(__name__)

NOTIFICATION_TYPES = ("created", "cancelled", "rescheduled", "approved", "picked-up")
ADMIN_MAIL_SUBJECT = "Received a new booking request."


def _admin_content(user, pickup):
    return f"You have received a new pickup request {pickup.pickup_id} from {user.get_full_name()}.\n"


def _build_content(notif_type, user, pickup):
    if notif_type == "created":
        return f"Your pickup request {pickup.pickup_id} has been received."
    if notif_type == "cancelled":
        return f"Your pickup request {pickup.pickup_id} has been cancelled"
    if notif_type == "rescheduled":
        return f"Pickup request {pickup.pickup_id} has been rescheduled to {pickup.pickup_date}"
    if notif_type == "approved":
        content = f"Pickup request {pickup.pickup_id} has been approved for pickup on {pickup.pickup_date}."
        if pickup.pickup_boy:
            content += f" Pickup boy: {pickup.pickup_boy}"
        return content
    return f"Pickup request {pickup.pickup_id} has been picked up."


def _send_admin_mail(plain_text, html_message, recipients):
    send_mail(
        ADMIN_MAIL_SUBJECT,
        plain_text,
        settings.DEFAULT_FROM_EMAIL,
        recipients,
        html_message=html_message,
    )


def _queue_admin_mail(user, content):
    recipients = settings.ADMIN_NOTIFICATION_EMAILS
    if not recipients:
        return
    html_message = render_to_string(
        "mail-templates/admin-mail.html",
        {"user": user, "content": content, "year": datetime.now().year},
    )
    run_in_background(_send_admin_mail, strip_tags(html_message), html_message, recipients)


def _create_admin_notification(user, pickup):
    admins = get_user_model().objects.filter(role__in=ADMIN_ROLES, is_active=True)
    content = _admin_content(user, pickup)
    notification = Notifications.objects.create(
        sent_to="Admin",
        subject="New Pickup Request",
        content=content,
        url=reverse("site_admin:view-request", kwargs={"pk": str(pickup.pickup_id)}),
    )
    Recipients.objects.bulk_create(
        [Recipients(notification=notification, recipient=admin) for admin in admins]
    )
    return content


def _dispatch_side_effects(notif_type, user, pickup):
    if notif_type == "created":
        content = _create_admin_notification(user, pickup)
        if user.phone:
            run_in_background(send_request_received, user.phone)
        _queue_admin_mail(user, content)
    elif notif_type == "approved":
        pickup_boy = pickup.pickup_boy
        if user.phone and pickup_boy:
            run_in_background(
                send_pickup_details, user.phone, pickup_boy.full_name, pickup_boy.phone
            )


def create_notification(*, user, pickup, notif_type):
    if not isinstance(pickup, Pickup):
        raise ValueError("'pickup' needs to be an instance of class Pickup")
    if notif_type not in NOTIFICATION_TYPES:
        raise ValueError(f"notif_type needs to be one of {NOTIFICATION_TYPES}")

    content = _build_content(notif_type, user, pickup)
    notification = Notifications.objects.create(
        sent_to="Customer",
        subject=f"Pickup Request {notif_type}",
        content=content,
        url=reverse("customer:view-order", kwargs={"pk": pickup.pickup_id}),
    )
    Recipients.objects.create(notification=notification, recipient=user)

    try:
        _dispatch_side_effects(notif_type, user, pickup)
    except Exception:
        logger.exception("Notification side effects failed for pickup %s", pickup.pickup_id)
    return notification
