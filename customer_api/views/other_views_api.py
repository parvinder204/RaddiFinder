from django.core.exceptions import ValidationError
from django.db.models import F, Sum
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common_models.models import City, Item, Pickup, PickupItems, State
from common_models.services import (
    PickupNotFound,
    PickupRequestError,
    add_items,
    create_pickup_request,
    ensure_editable,
    get_customer_pickup,
    items_from_legacy_lists,
    remove_item,
    update_pickup_address,
    with_amounts,
)
from customer_api.serializer import (
    CitiesSerializer,
    DashboardItemsSerializer,
    HistoryListSerializer,
    StatesSerializer,
    ViewOrderListSerializer,
)
from notifications.utils import create_notification


def _legacy(kind, message):
    return Response(f"{{'{kind}':'{message}'}}")


def _as_list(data, key):
    if hasattr(data, "getlist"):
        return data.getlist(key)
    value = data.get(key, [])
    return value if isinstance(value, list) else [value]


class PublicListAPIView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    queryset = None
    serializer_class = None

    def get(self, request, format=None):
        serializer = self.serializer_class(self.queryset.all(), many=True)
        return Response(serializer.data)


class DashboardItemsApi(PublicListAPIView):
    """
    Dashboard all item,
    """

    queryset = Item.objects.all()
    serializer_class = DashboardItemsSerializer


class StateApi(PublicListAPIView):
    """
    State all item,
    """

    queryset = State.objects.all()
    serializer_class = StatesSerializer


class CityApi(PublicListAPIView):
    """
    City all item,
    """

    queryset = City.objects.all()
    serializer_class = CitiesSerializer


class HistoryListApi(APIView):
    """
    History all item,
    """

    def get(self, request, format=None):
        pickups = list(with_amounts(Pickup.objects.filter(customer=request.user)))
        if not pickups:
            return Response({"error": "History is blank"})

        data = HistoryListSerializer(pickups, many=True).data
        for row, pickup in zip(data, pickups):
            row["estimated_amount"] = pickup.estimated_amount
            row["total_amount"] = pickup.total_amount
        return Response(data)


class ViewOrderListApi(APIView):
    """
    View order list
    """

    def get(self, request, view_id, format=None):
        try:
            pickup = Pickup.objects.select_related("customer").get(
                pickup_id=view_id, customer=request.user
            )
        except (Pickup.DoesNotExist, ValidationError, ValueError):
            raise NotFound("Order not found")

        pickup_items = (
            PickupItems.objects.filter(pickup=pickup)
            .select_related("item")
            .annotate(
                total_amount=F("actual_quantity") * F("final_price"),
                estimated_amount=F("quantity") * F("item__price"),
            )
        )
        items = {}
        for row in pickup_items:
            items[row.item.name] = {
                "item_reference": row.item.reference,
                "item_name": row.item.name,
                "item_price": row.final_price or row.item.price,
                "item_unit": row.item.unit,
                "item_quantity": row.actual_quantity or row.quantity,
                "item_amount": row.total_amount or row.estimated_amount,
            }

        data = ViewOrderListSerializer(pickup).data
        data["pickup_items"] = items
        data["final_amount"] = pickup_items.aggregate(final_amount=Sum("total_amount"))["final_amount"]
        data["expected_amount"] = pickup_items.aggregate(expected_amount=Sum("estimated_amount"))["expected_amount"]
        data["customer_name"] = pickup.customer.get_full_name()
        return Response(data)


class ItemAddApi(APIView):
    """
    Add Item for a customer
    """

    def post(self, request):
        try:
            pickup = get_customer_pickup(request.user, request.data.get("pickup_id"))
            if request.data.get("items") is not None:
                raw_items = request.data.get("items")
            else:
                raw_items = items_from_legacy_lists(
                    _as_list(request.data, "checks"), _as_list(request.data, "quantity")
                )
            add_items(pickup, raw_items)
        except PickupNotFound:
            raise NotFound("Request not found")
        except PickupRequestError as exc:
            return _legacy("error", str(exc))
        return _legacy("success", "Request Successfully Updated")


class ItemDeleteApi(APIView):
    """
    Delete Item for a customer
    """

    def delete(self, request, pk):
        row = (
            PickupItems.objects.select_related("pickup")
            .filter(pk=pk, pickup__customer=request.user)
            .first()
        )
        if row is None:
            raise NotFound("Item not found")
        try:
            remove_item(row.pickup, row.pk)
        except PickupRequestError as exc:
            return _legacy("error", str(exc))
        return _legacy("success", "Request Successfully Deleted")


class UpdateAddressApi(APIView):
    """
    Update address for a customer after adding Items
    """

    def put(self, request, requested_id):
        try:
            pickup = get_customer_pickup(request.user, requested_id)
            ensure_editable(pickup, "update")
            update_pickup_address(
                pickup,
                address=request.data.get("address"),
                state_id=request.data.get("state"),
                city_id=request.data.get("city"),
                pin_code=request.data.get("pin_code"),
                require_serviceable=True,
            )
        except PickupNotFound:
            raise NotFound("Request not found")
        except PickupRequestError as exc:
            return _legacy("error", str(exc))
        return _legacy("success", "Request Successfully Updated")


class ConfirmRequestApi(APIView):
    """
    Confirm request order
    """

    def post(self, request):
        data = request.data
        try:
            pickup = create_pickup_request(
                customer=request.user,
                pickup_date=data.get("date"),
                time_slot=data.get("time-slot"),
                notes=data.get("notes"),
                address=data.get("address"),
                state_id=data.get("state"),
                city_id=data.get("city"),
                pin_code=data.get("pin-code"),
                raw_items=data.get("data-list"),
            )
        except PickupRequestError as exc:
            return _legacy("error", str(exc))

        create_notification(user=request.user, pickup=pickup, notif_type="created")
        return Response("{'success': 'Request successfully created'}")