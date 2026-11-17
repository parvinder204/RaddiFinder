from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from common_models.models import Pickup, PickupItems
from common_models.services import (
    PickupRequestError,
    add_items,
    create_pickup_request,
    ensure_editable,
    parse_item_selection,
)


def booking(customer, city, item, **overrides):
    data = {
        "customer": customer,
        "pickup_date": (timezone.localdate() + timedelta(days=1)).isoformat(),
        "time_slot": "9-10",
        "notes": "",
        "address": "Street 1",
        "state_id": str(city.state_id),
        "city_id": str(city.id),
        "pin_code": "160055",
        "raw_items": [{"id": str(item.id), "quantity": "2"}],
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
def test_parse_item_selection_returns_quantized_decimals(paper):
    selection = parse_item_selection([{"id": str(paper.id), "quantity": "1.5"}])
    assert selection == [(paper, Decimal("1.500"))]


@pytest.mark.django_db
def test_parse_item_selection_sums_duplicate_items(paper):
    selection = parse_item_selection(
        [{"id": str(paper.id), "quantity": "1"}, {"id": str(paper.id), "quantity": "2"}]
    )
    assert selection == [(paper, Decimal("3.000"))]


@pytest.mark.django_db
@pytest.mark.parametrize("quantity", ["0", "-1", "abc", "1000", "nan"])
def test_parse_item_selection_rejects_bad_quantities(paper, quantity):
    with pytest.raises(PickupRequestError):
        parse_item_selection([{"id": str(paper.id), "quantity": quantity}])


@pytest.mark.django_db
def test_parse_item_selection_rejects_unknown_item(paper):
    with pytest.raises(PickupRequestError):
        parse_item_selection([{"id": "00000000-0000-0000-0000-000000000000", "quantity": "1"}])


@pytest.mark.django_db
def test_parse_item_selection_rejects_empty_input():
    with pytest.raises(PickupRequestError):
        parse_item_selection([])


@pytest.mark.django_db
def test_create_pickup_request_stores_items(customer, city, paper):
    pickup = create_pickup_request(**booking(customer, city, paper))
    assert pickup.status == "Requested"
    row = PickupItems.objects.get(pickup=pickup)
    assert row.item == paper
    assert row.quantity == Decimal("2.000")


@pytest.mark.django_db
def test_create_pickup_request_rejects_same_day_by_default(customer, city, paper):
    today = timezone.localdate().isoformat()
    with pytest.raises(PickupRequestError, match="today or a previous day"):
        create_pickup_request(**booking(customer, city, paper, pickup_date=today))
    assert not Pickup.objects.exists()


@pytest.mark.django_db
def test_lead_days_setting_controls_earliest_date(customer, city, paper, settings):
    settings.PICKUP_MIN_LEAD_DAYS = 3
    too_soon = (timezone.localdate() + timedelta(days=2)).isoformat()
    on_time = (timezone.localdate() + timedelta(days=3)).isoformat()
    with pytest.raises(PickupRequestError, match="3 days"):
        create_pickup_request(**booking(customer, city, paper, pickup_date=too_soon))
    create_pickup_request(**booking(customer, city, paper, pickup_date=on_time))


@pytest.mark.django_db
def test_zero_lead_days_allows_same_day_but_not_past(customer, city, paper, settings):
    settings.PICKUP_MIN_LEAD_DAYS = 0
    today = timezone.localdate()
    create_pickup_request(**booking(customer, city, paper, pickup_date=today.isoformat()))
    yesterday = (today - timedelta(days=1)).isoformat()
    with pytest.raises(PickupRequestError, match="past"):
        create_pickup_request(**booking(customer, city, paper, pickup_date=yesterday))


@pytest.mark.django_db
def test_create_pickup_request_requires_serviceable_city(customer, closed_city, paper):
    with pytest.raises(PickupRequestError, match="not available"):
        create_pickup_request(**booking(customer, closed_city, paper))


@pytest.mark.django_db
def test_create_pickup_request_requires_address(customer, city, paper):
    with pytest.raises(PickupRequestError, match="Address"):
        create_pickup_request(**booking(customer, city, paper, address="  "))


@pytest.mark.django_db
def test_create_pickup_request_rejects_unknown_time_slot(customer, city, paper):
    with pytest.raises(PickupRequestError, match="time slot"):
        create_pickup_request(**booking(customer, city, paper, time_slot="23-24"))


@pytest.mark.django_db
@pytest.mark.parametrize("status", ["Cancelled", "Picked-up"])
def test_locked_statuses_block_edits(pickup, status):
    pickup.status = status
    with pytest.raises(PickupRequestError):
        ensure_editable(pickup)


@pytest.mark.django_db
@pytest.mark.parametrize("status", ["Requested", "Approved", "Rescheduled"])
def test_open_statuses_allow_edits(pickup, status):
    pickup.status = status
    ensure_editable(pickup)


@pytest.mark.django_db
def test_add_items_merges_existing_rows(pickup, paper, metal):
    add_items(
        pickup,
        [{"id": str(paper.id), "quantity": "1"}, {"id": str(metal.id), "quantity": "4"}],
    )
    assert PickupItems.objects.get(pickup=pickup, item=paper).quantity == Decimal("3.000")
    assert PickupItems.objects.get(pickup=pickup, item=metal).quantity == Decimal("4.000")


@pytest.mark.django_db
def test_add_items_is_blocked_on_cancelled_pickup(pickup, paper):
    pickup.status = "Cancelled"
    with pytest.raises(PickupRequestError):
        add_items(pickup, [{"id": str(paper.id), "quantity": "1"}])
