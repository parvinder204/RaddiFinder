import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F, Sum
from django.utils import timezone

from .models import City, Item, Pickup, PickupItems, State
from .utils import is_valid_image, to_uuid

LOCKED_STATUSES = ("Cancelled", "Picked-up")
MAX_QUANTITY = Decimal("1000")
MAX_IMAGE_BYTES = 5 * 1024 * 1024
PIN_CODE_LENGTH = 6


class PickupRequestError(Exception):
    pass


class PickupNotFound(PickupRequestError):
    pass


def with_amounts(queryset):
    return queryset.annotate(
        estimated_amount=Sum(F("pickupitems__quantity") * F("pickupitems__item__price")),
        total_amount=Sum(F("pickupitems__actual_quantity") * F("pickupitems__final_price")),
    )


def _parse_quantity(value):
    try:
        quantity = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise PickupRequestError("Invalid item quantity.")
    if not quantity.is_finite() or quantity <= 0 or quantity >= MAX_QUANTITY:
        raise PickupRequestError("Invalid item quantity.")
    return quantity.quantize(Decimal("0.001"))


def _parse_pickup_date(value):
    try:
        pickup_date = datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        raise PickupRequestError("Invalid pickup date.")
    if pickup_date <= timezone.localdate():
        raise PickupRequestError("Pickup date cannot be today or a previous day.")
    return pickup_date


def _resolve_location(state_id, city_id, require_serviceable=False):
    try:
        state = State.objects.get(pk=to_uuid(state_id))
        city = City.objects.get(pk=to_uuid(city_id))
    except (State.DoesNotExist, City.DoesNotExist):
        raise PickupRequestError("Select a valid state and city.")
    if city.state_id != state.pk:
        raise PickupRequestError("Select a valid state and city.")
    if require_serviceable and not city.available:
        raise PickupRequestError("Pickups are not available in the selected city.")
    return state, city


def _clean_address(address, pin_code):
    address = (address or "").strip()
    pin_code = (pin_code or "").strip()
    if not address:
        raise PickupRequestError("Address is required.")
    if len(pin_code) > PIN_CODE_LENGTH:
        raise PickupRequestError("Enter a valid pin code.")
    return address, pin_code


def _clean_time_slot(value):
    slot = (value or "").strip() or None
    if slot and slot not in dict(Pickup.TIME_SLOTS):
        raise PickupRequestError("Select a valid time slot.")
    return slot


def _validate_image(image):
    if image is None:
        return
    if image.size > MAX_IMAGE_BYTES:
        raise PickupRequestError("Image is too large.")
    content_type = getattr(image, "content_type", "")
    if content_type and not content_type.startswith("image/"):
        raise PickupRequestError("Invalid image.")
    if not is_valid_image(image):
        raise PickupRequestError("Invalid image.")


def parse_item_selection(raw_items):
    if isinstance(raw_items, (str, bytes)):
        try:
            raw_items = json.loads(raw_items)
        except ValueError:
            raise PickupRequestError("Invalid item data.")
    if not isinstance(raw_items, list) or not raw_items:
        raise PickupRequestError("Select at least one item.")

    quantities = {}
    for entry in raw_items:
        try:
            item_id = to_uuid(entry["id"])
            raw_quantity = entry["quantity"]
        except (KeyError, TypeError):
            raise PickupRequestError("Invalid item data.")
        if item_id is None:
            raise PickupRequestError("Invalid item data.")
        total = quantities.get(item_id, Decimal(0)) + _parse_quantity(raw_quantity)
        if total >= MAX_QUANTITY:
            raise PickupRequestError("Invalid item quantity.")
        quantities[item_id] = total

    items = Item.objects.in_bulk(list(quantities))
    if len(items) != len(quantities):
        raise PickupRequestError("Selected item not found.")
    return [(items[item_id], quantity) for item_id, quantity in quantities.items()]


def create_pickup_request(
    *,
    customer,
    pickup_date,
    time_slot,
    notes,
    address,
    state_id,
    city_id,
    pin_code,
    raw_items,
    image=None,
):
    date_value = _parse_pickup_date(pickup_date)
    selection = parse_item_selection(raw_items)
    state, city = _resolve_location(state_id, city_id, require_serviceable=True)
    address, pin_code = _clean_address(address, pin_code)
    slot = _clean_time_slot(time_slot)
    _validate_image(image)

    with transaction.atomic():
        pickup = Pickup.objects.create(
            customer=customer,
            status="Requested",
            pickup_date=date_value,
            time_slot=slot,
            notes=(notes or "").strip(),
            address=address,
            state=state,
            city=city,
            pin_code=pin_code,
            image=image,
        )
        PickupItems.objects.bulk_create(
            [PickupItems(pickup=pickup, item=item, quantity=quantity) for item, quantity in selection]
        )
    return pickup


def get_customer_pickup(customer, pickup_id):
    try:
        return Pickup.objects.get(pickup_id=pickup_id, customer=customer)
    except (Pickup.DoesNotExist, ValidationError, ValueError, TypeError):
        raise PickupNotFound("Request not found.")


def ensure_editable(pickup, action="Change"):
    if pickup.status in LOCKED_STATUSES:
        raise PickupRequestError(f"You Cannot {action} after Cancel or Pickup Status")


def update_pickup_address(pickup, *, address, state_id, city_id, pin_code, require_serviceable=False):
    address, pin_code = _clean_address(address, pin_code)
    state, city = _resolve_location(state_id, city_id, require_serviceable=require_serviceable)
    pickup.address = address
    pickup.state = state
    pickup.city = city
    pickup.pin_code = pin_code
    pickup.save()
    return pickup


def items_from_legacy_lists(selected_ids, quantities):
    """Convert the old ``checks`` + ``quantity`` lists into ``[{"id", "quantity"}]``.

    Old clients send one quantity per catalogue item, in catalogue order. If the
    number of quantities does not match the catalogue the request is rejected
    instead of silently pairing quantities with the wrong items.
    """
    selected_ids = list(selected_ids or [])
    if not selected_ids:
        return []

    ordered_ids = list(Item.objects.order_by("created", "id").values_list("id", flat=True))
    quantity_list = list(quantities or [])
    if len(quantity_list) != len(ordered_ids):
        raise PickupRequestError("Invalid item data.")

    quantity_by_item = dict(zip(ordered_ids, quantity_list))
    entries = []
    for raw_id in selected_ids:
        item_id = to_uuid(raw_id)
        if item_id not in quantity_by_item:
            raise PickupRequestError("Invalid item data.")
        entries.append({"id": str(item_id), "quantity": quantity_by_item[item_id]})
    return entries


def items_from_post(data):
    """Build ``[{"id", "quantity"}]`` from the add-items form.

    The form submits ``quantity_<item id>`` next to each checkbox, so quantities
    are matched to items by id. Forms that still send ``quantity[]`` fall back to
    the positional lists.
    """
    selected_ids = data.getlist("checks[]")
    entries = []
    for raw_id in selected_ids:
        item_id = to_uuid(raw_id)
        if item_id is None:
            raise PickupRequestError("Invalid item data.")
        field = f"quantity_{item_id}"
        if field not in data:
            return items_from_legacy_lists(selected_ids, data.getlist("quantity[]"))
        entries.append({"id": str(item_id), "quantity": data.get(field)})
    return entries


def add_items(pickup, raw_items):
    """Add items to a pickup. ``raw_items`` uses the same format as create_pickup_request."""
    ensure_editable(pickup, "Change")
    selection = parse_item_selection(raw_items)

    try:
        with transaction.atomic():
            for item, quantity in selection:
                row = PickupItems.objects.filter(pickup=pickup, item=item).first()
                if row is None:
                    PickupItems.objects.create(pickup=pickup, item=item, quantity=quantity)
                    continue
                total = (row.quantity or Decimal(0)) + quantity
                if total >= MAX_QUANTITY:
                    raise PickupRequestError("Invalid item quantity.")
                row.quantity = total
                row.save()
    except IntegrityError:
        raise PickupRequestError("Item was already added. Please try again.")


def remove_item(pickup, row_id):
    ensure_editable(pickup, "delete")
    row_uuid = to_uuid(row_id)
    if row_uuid is None:
        raise PickupRequestError("Item not found.")
    deleted, _ = PickupItems.objects.filter(pk=row_uuid, pickup=pickup).delete()
    if not deleted:
        raise PickupRequestError("Item not found.")