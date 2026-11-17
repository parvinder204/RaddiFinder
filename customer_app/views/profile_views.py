from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView

from accounts.restriction import RestrictUserMixin
from accounts.utils import (
    EMAIL_IN_USE_MESSAGE,
    ProfileValidationError,
    clean_email,
    clean_name,
    clean_pin_code,
    ensure_email_available,
)
from common_models.models import City, State
from common_models.pagination import list_context, paginate
from common_models.services import MAX_IMAGE_BYTES
from common_models.utils import is_valid_image, to_uuid
from notifications.models import Recipients


class AccountSettingsView(RestrictUserMixin, ListView):
    login_url = reverse_lazy("customer:phone-number")
    template_name = "customer/settings.html"
    model = State
    role_name = "Customer"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["city_list"] = City.objects.filter(state=self.request.user.state)
        return context

    def post(self, request):
        data = request.POST
        state = State.objects.filter(pk=to_uuid(data.get("state"))).first()
        city = City.objects.filter(pk=to_uuid(data.get("city")), state=state).first() if state else None
        if city is None:
            messages.error(request, "Select a valid state and city.")
            return redirect("customer:account-settings")

        image = request.FILES.get("image")
        if image and (image.size > MAX_IMAGE_BYTES or not is_valid_image(image)):
            messages.error(request, "Upload a valid image under 5 MB.")
            return redirect("customer:account-settings")

        try:
            first_name = clean_name(data.get("first_name"), "First name")
            last_name = clean_name(data.get("last_name"), "Last name")
            email = clean_email(data.get("email"))
            ensure_email_available(email, request.user)
            pin_code = clean_pin_code(data.get("pin_code"))
        except ProfileValidationError as exc:
            messages.error(request, str(exc))
            return redirect("customer:account-settings")

        user = request.user
        if image:
            user.image = image
        user.first_name = first_name
        user.last_name = last_name
        user.email = email or None
        user.address = data.get("address", "").strip()
        user.state = state
        user.city = city
        user.pin_code = pin_code

        try:
            user.save()
        except IntegrityError:
            messages.error(request, EMAIL_IN_USE_MESSAGE)
        else:
            messages.success(request, "Account Details successfully saved")
        return redirect("customer:account-settings")


class NotificationView(RestrictUserMixin, View):
    role_name = "Customer"
    login_url = reverse_lazy("customer:phone-number")

    def get(self, request, *args, **kwargs):
        recipients = (
            Recipients.objects.filter(recipient=request.user)
            .select_related("notification")
            .order_by("-notification__created", "pk")
        )
        result = paginate(request, recipients)
        notifications = list(result.page.object_list)
        unread = [row.pk for row in notifications if not row.read]
        if unread:
            Recipients.objects.filter(pk__in=unread).update(read=True)
        context = {"notif_list": notifications, **list_context(result)}
        return render(request, "customer/notification.html", context)