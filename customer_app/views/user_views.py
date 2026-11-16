from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import ListView

from accounts.models import Person
from accounts.restriction import RestrictUserMixin
from accounts.roles import ADMIN_ROLES
from accounts.throttling import otp_send_limited, otp_verify_limited
from accounts.utils import (
    ProfileValidationError,
    clean_email,
    clean_name,
    clean_pin_code,
    safe_redirect_url,
)
from accounts.services import (
    OTPDeliveryError,
    OTPError,
    OTPExpired,
    OTPNotFound,
    consume_verified_otp,
    get_or_create_customer,
    is_valid_phone,
    issue_otp,
    revoke_api_tokens,
    valid_till_display,
    verify_otp,
)
from common_models.models import City, State
from common_models.utils import to_uuid

LOGIN_BACKEND = "django.contrib.auth.backends.ModelBackend"
RESET_SESSION_KEY = "password_reset_phone"


THROTTLED_MESSAGE = "Too many requests. Try again later."


def _json(status, **extra):
    return JsonResponse({"status": status, **extra})


def _send_throttled():
    return JsonResponse({"status": "fail", "message": THROTTLED_MESSAGE}, status=429)


def _delivery_failed():
    return JsonResponse({"status": "fail", "message": OTPDeliveryError.message}, status=503)


def _store_next_url(request):
    default = reverse("customer:select-items")
    request.session["next"] = safe_redirect_url(request, request.GET.get("next"), default)


def _has_name(phone):
    return (
        Person.objects.filter(phone=phone)
        .exclude(first_name__isnull=True)
        .exclude(first_name="")
        .exists()
    )


def _verify_and_login(request, phone, code, *, require_name):
    if otp_verify_limited(request):
        return _json(THROTTLED_MESSAGE)
    if not is_valid_phone(phone):
        return _json("Invalid OTP.")

    first_name = last_name = ""
    if require_name and not _has_name(phone):
        first_name = request.POST.get("fname", "").strip()
        last_name = request.POST.get("lname", "").strip()
        if not (first_name and last_name):
            return _json("Invalid input")

    try:
        verify_otp(phone, code, consume=True)
    except OTPError as exc:
        return _json(exc.message)

    user, _created = get_or_create_customer(phone)
    if first_name and not user.first_name:
        user.first_name = first_name[:50]
        user.last_name = last_name[:50]
        user.save()

    if not user.is_active:
        return _json("Your account has been deactivated.")

    login(request, user, backend=LOGIN_BACKEND)
    # login() rotates the CSRF token, so hand the new one to the page that is still open.
    return _json("login_done", u=user.phone, csrf_token=get_token(request))


@require_POST
def popup_login(request):
    action = request.POST.get("action")
    phone = request.POST.get("phone", "")

    if action == "otp_sent":
        if otp_send_limited(request):
            return _send_throttled()
        if not is_valid_phone(phone):
            return _json("fail")
        try:
            otp = issue_otp(phone)
        except OTPDeliveryError:
            return _delivery_failed()
        return _json("sent", show=not _has_name(phone), valid_till=valid_till_display(otp))

    if action == "otp_verify":
        return _verify_and_login(request, phone, request.POST.get("otp", ""), require_name=True)

    return redirect("customer:select-items")


@require_http_methods(["GET", "POST"])
def forgot_new_password(request):
    phone = request.session.get(RESET_SESSION_KEY)
    if not phone:
        messages.error(request, "Session expired. Try again.")
        return redirect("customer:forgot-password")

    if request.method == "GET":
        return render(request, "customer/forgot-new.html")

    password = request.POST.get("password1", "")
    confirmation = request.POST.get("password2", "")

    if password != confirmation:
        messages.error(request, "Passwords do not match.")
        return redirect("customer:forgot-new")
    try:
        validate_password(password, user=Person.objects.filter(phone=phone).first())
    except ValidationError as exc:
        for error in exc.messages:
            messages.error(request, error)
        return redirect("customer:forgot-new")

    user = None
    with transaction.atomic():
        if consume_verified_otp(phone):
            user = Person.objects.filter(phone=phone).first()
            if user is not None:
                user.set_password(password)
                user.save()
                revoke_api_tokens(user)

    request.session.pop(RESET_SESSION_KEY, None)
    request.session.pop("phone", None)

    if user is None:
        messages.error(request, "Session expired. Try again.")
        return redirect("customer:forgot-password")

    messages.success(request, "Password changed successfully.")
    if user.is_superuser or user.is_staff:
        return redirect("site_admin:login")
    return redirect("customer:phone-number")


@require_http_methods(["GET", "POST"])
def customer_forgot_password(request):
    if request.method == "GET":
        return render(request, "customer/forgot-password.html")

    if "otp_sent" in request.POST:
        if otp_send_limited(request):
            return _send_throttled()
        phone = request.POST.get("phone", "")
        if not is_valid_phone(phone) or not Person.objects.filter(phone=phone).exists():
            return _json("fail")
        request.session["phone"] = phone
        request.session.pop(RESET_SESSION_KEY, None)
        try:
            issue_otp(phone)
        except OTPDeliveryError:
            return _delivery_failed()
        return _json("sent")

    if "otp_next" in request.POST:
        if otp_verify_limited(request):
            return JsonResponse({"status": "fail", "message": THROTTLED_MESSAGE}, status=429)
        phone = request.session.get("phone", "")
        try:
            verify_otp(phone, request.POST.get("otp", ""))
        except OTPError as exc:
            return JsonResponse({"status": "fail", "message": exc.message}, status=400)
        request.session[RESET_SESSION_KEY] = phone
        return _json("otp checked")

    return JsonResponse({"status": "fail"}, status=400)


@require_http_methods(["GET", "POST"])
def customer_phone_number(request):
    if request.method == "GET":
        if request.user.is_authenticated and request.user.role in ADMIN_ROLES:
            return redirect("site_admin:dashboard")
        _store_next_url(request)
        return render(request, "customer/phone-number.html")

    action = request.POST.get("action")
    phone = request.POST.get("phone", "")

    if action == "otp_sent":
        if otp_send_limited(request):
            return _send_throttled()
        if not is_valid_phone(phone):
            return _json("fail")
        request.session["phone"] = phone
        try:
            otp = issue_otp(phone)
        except OTPDeliveryError:
            return _delivery_failed()
        return _json("sent", valid_till=valid_till_display(otp))

    if action == "otp_verify":
        return _verify_and_login(request, phone, request.POST.get("otp", ""), require_name=False)

    return redirect("customer:select-items")


@require_http_methods(["GET", "POST"])
def account_deactivation(request):
    if request.method == "GET":
        if request.user.is_authenticated and request.user.role in ADMIN_ROLES:
            return redirect("site_admin:dashboard")
        _store_next_url(request)
        return render(request, "customer/account_deactivation.html")

    if request.POST.get("action") != "otp_verify":
        return redirect("customer:select-items")

    if otp_verify_limited(request):
        return _json(THROTTLED_MESSAGE)

    phone = request.POST.get("phone", "")
    if not is_valid_phone(phone):
        return _json("Invalid OTP.")

    try:
        verify_otp(phone, request.POST.get("otp", ""), consume=True)
    except OTPError as exc:
        return _json(exc.message)

    user = Person.objects.filter(phone=phone).first()
    if user is None:
        status = "User not found."
    elif not user.is_active:
        status = "Your account is already inactive."
    else:
        user.is_active = False
        user.save()
        revoke_api_tokens(user)
        status = "Account deactivated!"
    return _json(status, u=phone)


@require_POST
def create_otp(request):
    if otp_send_limited(request):
        return _send_throttled()
    phone = request.POST.get("phone", "")
    if not is_valid_phone(phone):
        return _json("fail")
    try:
        otp = issue_otp(phone)
    except OTPDeliveryError:
        return _delivery_failed()
    return _json("sent", valid_till=valid_till_display(otp))


@require_POST
def check_otp(request):
    if otp_verify_limited(request):
        messages.error(request, THROTTLED_MESSAGE)
        return redirect("customer:forgot-password")

    phone = request.session.get("phone", "")
    try:
        verify_otp(phone, request.POST.get("otp", ""))
    except OTPNotFound:
        messages.error(request, "No OTP has been sent. Try again.")
        return redirect("customer:forgot-password")
    except OTPExpired:
        try:
            issue_otp(phone)
        except OTPDeliveryError:
            messages.error(request, OTPDeliveryError.message)
        else:
            messages.info(request, f"OTP is expired. New OTP sent to {phone}.")
        return redirect("customer:forgot-password")
    except OTPError as exc:
        messages.error(request, exc.message)
        return redirect("customer:forgot-password")

    request.session[RESET_SESSION_KEY] = phone
    return redirect("customer:forgot-new")


class CustomerDetailsPage(RestrictUserMixin, ListView):
    login_url = reverse_lazy("customer:phone-number")
    template_name = "customer/details.html"
    model = State
    role_name = "Customer"

    def post(self, request):
        try:
            first_name = clean_name(request.POST.get("first_name"), "First name")
            last_name = clean_name(request.POST.get("last_name"), "Last name")
            email = clean_email(request.POST.get("email"))
            pin_code = clean_pin_code(request.POST.get("pin-code"))
        except ProfileValidationError as exc:
            messages.error(request, str(exc))
            return redirect("customer:details")

        user = request.user
        user.first_name = first_name or None
        user.last_name = last_name or None
        user.email = email or None
        user.address = request.POST.get("address") or None
        user.pin_code = pin_code or None

        try:
            user.state = State.objects.get(id=to_uuid(request.POST.get("state")))
            user.city = City.objects.get(id=to_uuid(request.POST.get("city")))
        except (State.DoesNotExist, City.DoesNotExist):
            pass

        try:
            user.save()
        except IntegrityError:
            messages.error(request, f"Email '{user.email}' already in use")
            return redirect("customer:details")

        return redirect(request.session.get("next", reverse("customer:select-items")))