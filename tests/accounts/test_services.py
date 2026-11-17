from datetime import timedelta

import pytest
from django.utils import timezone

from accounts import services
from accounts.models import OTP, Person

PHONE = "9876543210"


@pytest.fixture
def sent(monkeypatch):
    messages = []

    def fake_send(phone, code):
        messages.append((phone, code))
        return True

    monkeypatch.setattr(services, "send_otp_message", fake_send)
    return messages


def wrong_code(otp):
    return "x" * len(otp.otp)


@pytest.mark.django_db
def test_issue_otp_creates_and_sends(sent, settings):
    otp = services.issue_otp(PHONE)
    assert sent == [(PHONE, otp.otp)]
    assert len(otp.otp) == settings.OTP_LENGTH
    assert OTP.objects.filter(phone=PHONE).count() == 1


@pytest.mark.django_db
def test_issue_otp_respects_resend_cooldown(sent, settings):
    settings.OTP_RESEND_COOLDOWN_SECONDS = 60
    services.issue_otp(PHONE)
    services.issue_otp(PHONE)
    assert len(sent) == 1


@pytest.mark.django_db
def test_issue_otp_removes_record_when_delivery_fails(monkeypatch):
    monkeypatch.setattr(services, "send_otp_message", lambda phone, code: False)
    with pytest.raises(services.OTPDeliveryError):
        services.issue_otp(PHONE)
    assert not OTP.objects.filter(phone=PHONE).exists()


@pytest.mark.django_db
def test_verify_otp_marks_code_correct(sent):
    otp = services.issue_otp(PHONE)
    services.verify_otp(PHONE, otp.otp)
    otp.refresh_from_db()
    assert otp.correct is True


@pytest.mark.django_db
def test_verify_otp_with_consume_deletes_record(sent):
    otp = services.issue_otp(PHONE)
    services.verify_otp(PHONE, otp.otp, consume=True)
    assert not OTP.objects.filter(phone=PHONE).exists()


@pytest.mark.django_db
def test_verify_otp_unknown_phone_raises_not_found():
    with pytest.raises(services.OTPNotFound):
        services.verify_otp(PHONE, "12345")


@pytest.mark.django_db
def test_wrong_codes_lock_the_otp(sent, settings):
    settings.OTP_MAX_ATTEMPTS = 3
    otp = services.issue_otp(PHONE)
    for _ in range(2):
        with pytest.raises(services.OTPInvalid):
            services.verify_otp(PHONE, wrong_code(otp))
    with pytest.raises(services.OTPLocked):
        services.verify_otp(PHONE, wrong_code(otp))
    with pytest.raises(services.OTPLocked):
        services.verify_otp(PHONE, otp.otp)


@pytest.mark.django_db
def test_expired_otp_is_rejected_and_removed(sent, settings):
    otp = services.issue_otp(PHONE)
    expired_at = timezone.now() - timedelta(minutes=settings.OTP_EXPIRY_MINUTES + 1)
    OTP.objects.filter(pk=otp.pk).update(created=expired_at)
    with pytest.raises(services.OTPExpired):
        services.verify_otp(PHONE, otp.otp)
    assert not OTP.objects.filter(phone=PHONE).exists()


@pytest.mark.django_db
def test_consume_verified_otp_works_once(sent):
    otp = services.issue_otp(PHONE)
    assert services.consume_verified_otp(PHONE) is False
    services.verify_otp(PHONE, otp.otp)
    assert services.consume_verified_otp(PHONE) is True
    assert services.consume_verified_otp(PHONE) is False


@pytest.mark.django_db
def test_purge_expired_otps_only_removes_old_records(sent, settings):
    old = services.issue_otp(PHONE)
    fresh = services.issue_otp("9876543299")
    expired_at = timezone.now() - timedelta(minutes=settings.OTP_EXPIRY_MINUTES + 1)
    OTP.objects.filter(pk=old.pk).update(created=expired_at)
    assert services.purge_expired_otps() == 1
    assert OTP.objects.filter(pk=fresh.pk).exists()


@pytest.mark.django_db
def test_get_or_create_customer_creates_once():
    user, created = services.get_or_create_customer(PHONE)
    assert created is True
    assert user.role == "Customer"
    assert not user.has_usable_password()
    again, created_again = services.get_or_create_customer(PHONE)
    assert created_again is False
    assert again.pk == user.pk
    assert Person.objects.filter(phone=PHONE).count() == 1


def test_is_valid_phone():
    assert services.is_valid_phone("9876543210")
    assert not services.is_valid_phone("98765")
    assert not services.is_valid_phone("98765abcde")
    assert not services.is_valid_phone(None)
