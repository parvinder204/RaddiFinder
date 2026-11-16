import hmac
import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from notifications.sms import send_otp_message

from .models import OTP, Person

PHONE_LENGTH = 10


class OTPError(Exception):
    message = "Invalid OTP."

    def __str__(self):
        return self.message


class OTPNotFound(OTPError):
    message = "Invalid OTP."


class OTPExpired(OTPError):
    message = "OTP expired."


class OTPInvalid(OTPError):
    message = "Invalid OTP."


class OTPLocked(OTPError):
    message = "Too many incorrect attempts. Request a new OTP."


class OTPDeliveryError(OTPError):
    message = "Could not send the OTP. Please try again."


def is_valid_phone(value):
    return isinstance(value, str) and value.isdigit() and len(value) == PHONE_LENGTH


def _generate_code():
    return "".join(secrets.choice(string.digits) for _ in range(settings.OTP_LENGTH))


def expires_at(otp):
    return otp.created + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)


def is_expired(otp):
    return timezone.now() >= expires_at(otp)


def is_locked(otp):
    return otp.attempts >= settings.OTP_MAX_ATTEMPTS


def valid_till_display(otp):
    return timezone.localtime(expires_at(otp)).strftime("%d %b, %Y, %I:%M %p")


def _cooldown_elapsed(otp):
    elapsed = (timezone.now() - otp.last_sent).total_seconds()
    return elapsed >= settings.OTP_RESEND_COOLDOWN_SECONDS


def issue_otp(phone):
    should_send = True
    with transaction.atomic():
        otp = OTP.objects.select_for_update().filter(phone=phone).first()

        if otp and (otp.correct or is_expired(otp)):
            otp.delete()
            otp = None
        elif otp and is_locked(otp):
            if _cooldown_elapsed(otp):
                otp.delete()
                otp = None
            else:
                should_send = False
        elif otp:
            if _cooldown_elapsed(otp):
                otp.last_sent = timezone.now()
                otp.save()
            else:
                should_send = False

        if otp is None:
            try:
                with transaction.atomic():
                    otp = OTP.objects.create(phone=phone, otp=_generate_code())
            except IntegrityError:
                otp = OTP.objects.get(phone=phone)
                should_send = False

    if should_send and not send_otp_message(phone, otp.otp):
        OTP.objects.filter(pk=otp.pk).delete()
        raise OTPDeliveryError()
    return otp


def verify_otp(phone, code, *, consume=False):
    error = None
    with transaction.atomic():
        otp = OTP.objects.select_for_update().filter(phone=phone).first()
        if otp is None:
            error = OTPNotFound
        elif is_expired(otp):
            otp.delete()
            error = OTPExpired
        elif is_locked(otp):
            error = OTPLocked
        elif not hmac.compare_digest(otp.otp, str(code or "")):
            otp.attempts += 1
            otp.save()
            error = OTPLocked if is_locked(otp) else OTPInvalid
        elif consume:
            otp.delete()
        else:
            otp.correct = True
            otp.save()

    if error is not None:
        raise error()
    return otp


def consume_verified_otp(phone):
    with transaction.atomic():
        otp = OTP.objects.select_for_update().filter(phone=phone, correct=True).first()
        if otp is None or is_expired(otp):
            return False
        otp.delete()
        return True


def purge_expired_otps():
    threshold = timezone.now() - timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    deleted, _ = OTP.objects.filter(created__lt=threshold).delete()
    return deleted


def get_or_create_customer(phone):
    try:
        with transaction.atomic():
            user, created = Person.objects.get_or_create(phone=phone, defaults={"role": "Customer"})
    except IntegrityError:
        user, created = Person.objects.get(phone=phone), False

    if created:
        user.set_unusable_password()
        user.save()
    elif not user.role:
        user.role = "Customer"
        user.save()
    return user, created


def revoke_api_tokens(user):
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)