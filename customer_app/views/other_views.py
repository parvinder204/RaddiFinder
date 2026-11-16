from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import F, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView, ListView

from accounts.decorators import role_required
from accounts.restriction import RestrictUserMixin
from common_models.models import City, Item, Pickup, PickupItems, State
from common_models.services import (
    PickupRequestError,
    add_items,
    create_pickup_request,
    ensure_editable,
    items_from_post,
    remove_item,
    update_pickup_address,
    with_amounts,
)
from common_models.utils import decode_file, render_to_pdf, to_uuid
from notifications.utils import create_notification


def _available_states():
    return State.objects.filter(city__available=True).distinct().order_by("name")


def _selected_item_ids(request):
    """Item ids posted back after login.

    The page joins the ids into one comma separated value, so split each value
    and keep only valid, unique UUIDs (they are written into the page's JavaScript).
    """
    item_ids = []
    for chunk in request.POST.getlist("product_id"):
        for raw in chunk.split(","):
            item_id = to_uuid(raw.strip())
            if item_id is not None and str(item_id) not in item_ids:
                item_ids.append(str(item_id))
    return item_ids


def _city_context(user):
    if not user.is_authenticated:
        return {}
    return {"city_list": City.objects.filter(state=user.state, available=True)}


class DashboardView(View):
    def get(self, request):
        return redirect("customer:select-items")


class SelectView(View):
    def get(self, request):
        context = {
            "item_list": Item.objects.all(),
            "state_list": _available_states(),
            **_city_context(request.user),
        }
        return render(request, "customer/select-items.html", context)

    def post(self, request):
        if "date" in request.POST:
            return self._create_request(request)

        context = {
            "item_list": Item.objects.all(),
            "step_out": "step_out" in request.POST,
            "state_list": _available_states(),
        }
        if "product_id" in request.POST:
            context["sel_items"] = _selected_item_ids(request)
            context.update(_city_context(request.user))
        return render(request, "customer/select-items.html", context)

    def _create_request(self, request):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to place a request.")
            return redirect("customer:select-items")

        try:
            pickup = create_pickup_request(
                customer=request.user,
                pickup_date=request.POST.get("date"),
                time_slot=request.POST.get("time-slot"),
                notes=request.POST.get("notes"),
                address=request.POST.get("address"),
                state_id=request.POST.get("state"),
                city_id=request.POST.get("city"),
                pin_code=request.POST.get("pin-code"),
                raw_items=request.POST.get("data-list"),
                image=request.FILES.get("image_data"),
            )
        except PickupRequestError as exc:
            messages.error(request, str(exc))
            return redirect("customer:select-items")

        create_notification(user=request.user, pickup=pickup, notif_type="created")
        messages.success(request, "Request Successfully Created")
        return redirect("customer:select-items")


class HistoryView(RestrictUserMixin, ListView):
    login_url = reverse_lazy("customer:phone-number")
    role_name = "Customer"
    template_name = "customer/history.html"
    model = Pickup

    def get_queryset(self):
        return with_amounts(Pickup.objects.filter(customer=self.request.user))


class ViewOrderView(RestrictUserMixin, DetailView):
    template_name = "customer/view-order.html"
    model = Pickup
    login_url = reverse_lazy("customer:phone-number")
    role_name = "Customer"

    def get_queryset(self):
        return Pickup.objects.filter(customer=self.request.user)

    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except (ValidationError, ValueError):
            raise Http404

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pickup_items = (
            PickupItems.objects.filter(pickup=self.object)
            .select_related("item")
            .annotate(
                total_amount=F("actual_quantity") * F("final_price"),
                estimated_amount=F("quantity") * F("item__price"),
            )
        )
        context["pickup_items"] = pickup_items
        context["final_amount"] = pickup_items.aggregate(final_amount=Sum("total_amount"))["final_amount"]
        context["expected_amount"] = pickup_items.aggregate(expected_amount=Sum("estimated_amount"))["expected_amount"]
        context["state_list"] = State.objects.all()
        context["city_list"] = City.objects.all()
        context["item_list"] = Item.objects.order_by("created", "id")
        return context

    def post(self, request, *args, **kwargs):
        pickup = self.get_object()
        try:
            if "address_update" in request.POST:
                self._update_address(request, pickup)
            elif "add_item" in request.POST:
                self._add_items(request, pickup)
            elif "delete_item_submit" in request.POST:
                self._delete_item(request, pickup)
            elif "add_notes" in request.POST:
                self._add_notes(request, pickup)
        except PickupRequestError as exc:
            messages.error(request, str(exc))
        return redirect("customer:view-order", pk=pickup.pk)

    def _update_address(self, request, pickup):
        ensure_editable(pickup, "Change")
        update_pickup_address(
            pickup,
            address=request.POST.get("address"),
            state_id=request.POST.get("state"),
            city_id=request.POST.get("city"),
            pin_code=request.POST.get("pin_code"),
            require_serviceable=True,
        )
        messages.success(request, "Request Successfully Updated")

    def _add_items(self, request, pickup):
        add_items(pickup, items_from_post(request.POST))
        messages.success(request, "Request Successfully Updated")

    def _delete_item(self, request, pickup):
        remove_item(pickup, request.POST.get("item_delete_id"))
        messages.success(request, "Request Successfully Deleted")

    def _add_notes(self, request, pickup):
        ensure_editable(pickup, "Update notes")
        pickup.notes = request.POST.get("notes", "")
        pickup.save()
        messages.success(request, "Notes Successfully Added")


class ConfirmRequest(RestrictUserMixin, ListView):
    login_url = reverse_lazy("customer:phone-number")
    template_name = "customer/confirm-request.html"
    model = Item
    role_name = "Customer"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["state_list"] = State.objects.all()
        context["city_list"] = City.objects.filter(state=self.request.user.state)
        return context

    def post(self, request, *args, **kwargs):
        image_uri = request.POST.get("image_data")
        image = decode_file(image_uri)
        if image_uri and image is None:
            messages.error(request, "Invalid image.")
            return redirect("customer:confirm-request")

        try:
            pickup = create_pickup_request(
                customer=request.user,
                pickup_date=request.POST.get("date"),
                time_slot=request.POST.get("time-slot"),
                notes=request.POST.get("notes"),
                address=request.POST.get("address"),
                state_id=request.POST.get("state"),
                city_id=request.POST.get("city"),
                pin_code=request.POST.get("pin-code"),
                raw_items=request.POST.get("data-list"),
                image=image,
            )
        except PickupRequestError as exc:
            messages.error(request, str(exc))
            return redirect("customer:confirm-request")

        create_notification(user=request.user, pickup=pickup, notif_type="created")
        messages.success(request, "Request Successfully Created")
        return redirect("customer:select-items")


@role_required("Customer", "Admin", login_url="customer:phone-number")
def invoice_gen(request, uuid):
    try:
        pickup = Pickup.objects.select_related("customer").get(pickup_id=uuid)
    except (Pickup.DoesNotExist, ValidationError, ValueError):
        raise Http404

    if request.user.role == "Customer" and pickup.customer_id != request.user.pk:
        raise Http404

    pickup_items = (
        PickupItems.objects.filter(pickup=pickup)
        .select_related("item")
        .annotate(amount=F("actual_quantity") * F("final_price"))
    )
    context = {
        "pickup": pickup,
        "pickup_items": pickup_items,
        "total_amount": pickup_items.aggregate(total_amount=Sum("amount")),
    }
    pdf = render_to_pdf("mail-templates/invoice.html", context)
    if pdf is None:
        return HttpResponse("Unable to generate invoice.", status=500)
    return pdf