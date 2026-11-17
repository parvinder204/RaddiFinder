from decimal import Decimal

import pytest

from common_models.audit import pickup_item_snapshot, pickup_snapshot, record
from common_models.models import AuditLog, PickupItems


@pytest.mark.django_db
def test_record_stores_actor_and_target(admin_user):
    entry = record(admin_user, "pickup_deleted", "Pickup", "abc", {"status": "Requested"})
    stored = AuditLog.objects.get(pk=entry.pk)
    assert stored.actor == admin_user
    assert stored.action == "pickup_deleted"
    assert stored.target_type == "Pickup"
    assert stored.target_id == "abc"
    assert stored.snapshot == {"status": "Requested"}


@pytest.mark.django_db
def test_record_without_actor_is_allowed():
    entry = record(None, "pickup_deleted", "Pickup", "abc")
    assert entry.actor is None
    assert entry.snapshot == {}


@pytest.mark.django_db
def test_pickup_snapshot_captures_order_and_items(pickup):
    snapshot = pickup_snapshot(pickup)
    assert snapshot["pickup_id"] == str(pickup.pickup_id)
    assert snapshot["customer_phone"] == pickup.customer.phone
    assert snapshot["status"] == "Requested"
    assert snapshot["city"] == "Mohali"
    assert snapshot["items"][0]["item"] == "Paper"
    assert snapshot["items"][0]["quantity"] == Decimal("2.000")


@pytest.mark.django_db
def test_snapshot_is_json_serialisable_through_the_model(pickup, admin_user):
    entry = record(admin_user, "pickup_deleted", "Pickup", pickup.pickup_id, pickup_snapshot(pickup))
    entry.refresh_from_db()
    assert entry.snapshot["items"][0]["quantity"] == "2.000"


@pytest.mark.django_db
def test_pickup_item_snapshot_includes_final_figures(pickup):
    row = PickupItems.objects.get(pickup=pickup)
    row.actual_quantity = Decimal("3.00")
    row.final_price = Decimal("15.00")
    row.save()
    snapshot = pickup_item_snapshot(PickupItems.objects.select_related("item").get(pk=row.pk))
    assert snapshot["actual_quantity"] == Decimal("3.00")
    assert snapshot["final_price"] == Decimal("15.00")
