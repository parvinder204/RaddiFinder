import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import F, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from accounts.decorators import role_required
from accounts.restriction import RestrictUserMixin
from common_models.audit import pickup_item_snapshot, pickup_snapshot, record
from common_models.models import Cancellation, City, Item, Pickup, PickupBoy, PickupItems, State
from common_models.services import (
    MAX_QUANTITY,
    PickupRequestError,
    ensure_editable,
    update_pickup_address,
)
from common_models.utils import to_uuid
from notifications.utils import create_notification
from common_models.pagination import PaginatedSearchMixin, redirect_to_list

BOY_REQUIRED_STATUSES = ("Approved", "Picked-up", "Rescheduled")
RESCHEDULE_DATE_FORMAT = "%d %b, %Y"
QUANTITY_LIMIT = Decimal("10000")
PAYMENT_LIMIT = Decimal("1000000")
MIN_STATUS_SEARCH_LENGTH = 3
DATE_SEARCH_PATTERN = re.compile(r"^\d{1,2}-\d{1,2}-\d{4}$")
STATUS_KEYWORDS = {
    "requested": "Requested",
    "raised": "Requested",
    "approved": "Approved",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
    "picked-up": "Picked-up",
    "paid": "Picked-up",
    "rescheduled": "Rescheduled",
}


class RequestUpdateError(Exception):
    pass


def _decimal(value, limit):
    try:
        number = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        raise RequestUpdateError("Invalid amount entered")
    if not number.is_finite() or number < 0 or number >= limit:
        raise RequestUpdateError("Invalid amount entered")
    return number


def _status_clause(word):
    word = word.lower()
    if len(word) < MIN_STATUS_SEARCH_LENGTH:
        return Q()
    matched = {status for keyword, status in STATUS_KEYWORDS.items() if keyword.startswith(word)}
    return Q(status__in=matched) if matched else Q()


def _date_clause(word):
    if not DATE_SEARCH_PATTERN.match(word):
        return Q()
    try:
        day = datetime.strptime(word, "%d-%m-%Y").date()
    except ValueError:
        return Q()
    return Q(created__date=day) | Q(pickup_date=day)


def _get_pickup(pk):
    try:
        return Pickup.objects.get(pk=pk)
    except (Pickup.DoesNotExist, ValidationError, ValueError):
        raise Http404


class ManageRequestsView(PaginatedSearchMixin, RestrictUserMixin, ListView):
    model = Pickup
    template_name = "site_admin/manage-requests.html"
    login_url = reverse_lazy("site_admin:login")
    role_name = "Admin"
    search_fields = (
        "reference",
        "pickup_id",
        "customer__first_name",
        "customer__last_name",
        "customer__phone",
        "pickup_boy__full_name",
    )

    def get_queryset(self):
        return Pickup.objects.select_related("customer", "pickup_boy").order_by("-created", "pk")

    def search_clause(self, word):
        return _status_clause(word) | _date_clause(word)


class RequestRespondView(RestrictUserMixin, DetailView):
    model = Pickup
    template_name = "site_admin/view-request.html"
    login_url = reverse_lazy("site_admin:login")
    role_name = "Admin"

    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except (ValidationError, ValueError):
            raise Http404

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pickup = self.object
        pickup_items = (
            PickupItems.objects.filter(pickup=pickup)
            .select_related("item")
            .annotate(estimated_amount=F("quantity") * F("item__price"))
        )
        context["pickup_boy_list"] = PickupBoy.objects.filter(
            Q(employed=True) | Q(pk=pickup.pickup_boy_id)
        )
        context["state_list"] = State.objects.all()
        context["city_list"] = City.objects.filter(state=pickup.state)
        context["pickup_items"] = pickup_items
        context["final_amount"] = pickup_items.aggregate(final_amount=Sum("estimated_amount"))["final_amount"]
        context["item_list"] = Item.objects.all()
        return context

    def post(self, request, pk):
        pickup = _get_pickup(pk)
        target = reverse("site_admin:view-request", kwargs={"pk": str(pickup.pk)})
        status = request.POST.get("status", "")

        if status not in dict(Pickup.STATUS):
            messages.error(request, "Select a valid status")
            return redirect(target)

        try:
            with transaction.atomic():
                notification_type = self._apply_changes(pickup, status)
        except RequestUpdateError as exc:
            messages.error(request, str(exc))
            return redirect(target)

        if notification_type:
            create_notification(
                user=pickup.customer, pickup=pickup, notif_type=notification_type
            )

        messages.success(request, f"Request {pickup} successfully {status}")
        return redirect(target)

    def _apply_changes(self, pickup, status):
        previous_status = pickup.status
        previous_boy_id = pickup.pickup_boy_id

        additional_data = pickup.additional_data or {}
        additional_data["admin_notes"] = self.request.POST.get("notes", "")
        pickup.additional_data = additional_data
        pickup.status = status

        if status in BOY_REQUIRED_STATUSES:
            pickup.pickup_boy = self._resolve_pickup_boy(pickup)

        self._apply_item_data(pickup, self.request.POST.get("items_data"))

        if status == "Picked-up":
            pickup.payment = _decimal(self.request.POST.get("payment"), PAYMENT_LIMIT)

        if status == "Rescheduled":
            self._reschedule(pickup, additional_data)

        pickup.save()
        self._sync_cancellation(pickup, status, additional_data["admin_notes"])
        return self._notification_type(pickup, status, previous_status, previous_boy_id)

    def _sync_cancellation(self, pickup, status, reason):
        if status == "Cancelled":
            Cancellation.objects.update_or_create(
                pickup=pickup,
                defaults={"reason": reason.strip() or "Cancelled by admin"},
            )
        else:
            Cancellation.objects.filter(pickup=pickup).delete()

    def _notification_type(self, pickup, status, previous_status, previous_boy_id):
        if status == "Approved":
            changed = previous_status != "Approved" or previous_boy_id != pickup.pickup_boy_id
            return "approved" if changed else None
        if status == "Picked-up":
            return "picked-up" if previous_status != "Picked-up" else None
        if status == "Cancelled":
            return "cancelled" if previous_status != "Cancelled" else None
        if status == "Rescheduled":
            return "rescheduled"
        return None

    def _resolve_pickup_boy(self, pickup):
        boy_id = to_uuid(self.request.POST.get("pickup-boy"))
        try:
            return PickupBoy.objects.get(
                Q(employed=True) | Q(pk=pickup.pickup_boy_id), pk=boy_id
            )
        except PickupBoy.DoesNotExist:
            raise RequestUpdateError("Select a valid pickup boy")

    def _apply_item_data(self, pickup, raw_data):
        if not raw_data:
            return
        try:
            entries = json.loads(raw_data)
            parsed = [
                (
                    Item.objects.get(pk=to_uuid(entry["item_id"])),
                    _decimal(entry["actual_quantity"], QUANTITY_LIMIT),
                    _decimal(entry["actual_price"], QUANTITY_LIMIT),
                )
                for entry in entries
            ]
        except (ValueError, KeyError, TypeError, ObjectDoesNotExist):
            raise RequestUpdateError("Invalid item data")

        for item, actual_quantity, final_price in parsed:
            row = PickupItems.objects.filter(pickup=pickup, item=item).first()
            if row is None:
                if actual_quantity >= MAX_QUANTITY:
                    raise RequestUpdateError(
                        f"Quantity of a newly added item must be less than {MAX_QUANTITY:f}"
                    )
                row = PickupItems(pickup=pickup, item=item, quantity=actual_quantity)
            row.actual_quantity = actual_quantity
            row.final_price = final_price
            row.save()

    def _reschedule(self, pickup, additional_data):
        try:
            new_date = datetime.strptime(
                self.request.POST.get("reschedule-date", ""), RESCHEDULE_DATE_FORMAT
            ).date()
        except ValueError:
            raise RequestUpdateError("Select a valid reschedule date")

        time_slot = self.request.POST.get("time-slot", "")
        if time_slot and time_slot not in dict(Pickup.TIME_SLOTS):
            raise RequestUpdateError("Select a valid time slot")

        history = additional_data.get("reschedule_data", [])
        history.append(
            {
                "date": pickup.pickup_date.strftime(RESCHEDULE_DATE_FORMAT),
                "time_slot": pickup.time_slot,
            }
        )
        additional_data["reschedule_data"] = history

        pickup.status = "Approved"
        pickup.pickup_date = new_date
        pickup.time_slot = time_slot


@require_POST
@role_required("Admin", json=True)
def update_request_address(request):
    try:
        pickup = Pickup.objects.get(pk=request.POST["pickup_id"])
        update_pickup_address(
            pickup,
            address=request.POST.get("address"),
            state_id=request.POST.get("state"),
            city_id=request.POST.get("city"),
            pin_code=request.POST.get("pin_code"),
        )
    except (KeyError, ValueError, ValidationError, ObjectDoesNotExist):
        return JsonResponse({"status": False, "notes": "Request not found."}, status=404)
    except PickupRequestError as exc:
        return JsonResponse({"status": False, "notes": str(exc)}, status=400)
    return JsonResponse({"status": True, "notes": "Address updated successfully"})


@require_POST
@role_required("Admin", json=True)
def delete_pickup_item(request):
    row_id = to_uuid(request.POST.get("pickup_id"))
    if row_id is None:
        return JsonResponse({"status": False, "notes": "Invalid item."}, status=400)
    row = PickupItems.objects.select_related("pickup", "item").filter(pk=row_id).first()
    if row is None:
        return JsonResponse({"status": False, "notes": "Item not found."}, status=404)
    try:
        ensure_editable(row.pickup, "delete")
    except PickupRequestError as exc:
        return JsonResponse({"status": False, "notes": str(exc)}, status=400)
    with transaction.atomic():
        record(request.user, "pickup_item_deleted", "PickupItems", row.pk, pickup_item_snapshot(row))
        row.delete()
    return JsonResponse({"status": True, "notes": "Item successfully removed"})


@require_POST
@role_required("Admin", login_url="site_admin:login")
def Order_delete(request):
    pickup_id = to_uuid(request.POST.get("item_delete_id"))
    pickup = (
        Pickup.objects.select_related("customer", "city", "state", "pickup_boy")
        .filter(pickup_id=pickup_id)
        .first()
        if pickup_id
        else None
    )
    if pickup is None:
        messages.error(request, "Request not found")
        return redirect_to_list(request, "site_admin:manage-requests")
    with transaction.atomic():
        record(request.user, "pickup_deleted", "Pickup", pickup.pickup_id, pickup_snapshot(pickup))
        pickup.delete()
    messages.success(request, "Request Successfully Deleted")
    return redirect_to_list(request, "site_admin:manage-requests")