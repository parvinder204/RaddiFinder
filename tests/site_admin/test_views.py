from decimal import Decimal

import pytest
from django.urls import reverse

from common_models.models import AuditLog, Pickup, PickupItems
from site_admin.views.common_views import top_items_by_value


@pytest.mark.django_db
def test_customer_cannot_delete_pickup_items(customer_client, pickup):
    row = PickupItems.objects.get(pickup=pickup)
    response = customer_client.post(reverse("site_admin:delete-pickup-item"), {"pickup_id": row.pk})
    assert response.status_code == 403
    assert PickupItems.objects.filter(pk=row.pk).exists()


@pytest.mark.django_db
def test_admin_deletes_item_and_audit_entry_is_written(admin_client, admin_user, pickup):
    row = PickupItems.objects.get(pickup=pickup)
    response = admin_client.post(reverse("site_admin:delete-pickup-item"), {"pickup_id": row.pk})
    assert response.status_code == 200
    assert response.json()["status"] is True
    assert not PickupItems.objects.filter(pk=row.pk).exists()
    entry = AuditLog.objects.get(action="pickup_item_deleted")
    assert entry.actor == admin_user
    assert entry.target_id == str(row.pk)
    assert entry.snapshot["item"] == "Paper"


@pytest.mark.django_db
@pytest.mark.parametrize("status", ["Picked-up", "Cancelled"])
def test_items_of_closed_pickups_cannot_be_deleted(admin_client, pickup, status):
    pickup.status = status
    pickup.save()
    row = PickupItems.objects.get(pickup=pickup)
    response = admin_client.post(reverse("site_admin:delete-pickup-item"), {"pickup_id": row.pk})
    assert response.status_code == 400
    assert response.json()["status"] is False
    assert PickupItems.objects.filter(pk=row.pk).exists()
    assert not AuditLog.objects.exists()


@pytest.mark.django_db
def test_deleting_unknown_item_returns_not_found(admin_client):
    response = admin_client.post(
        reverse("site_admin:delete-pickup-item"),
        {"pickup_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_order_delete_removes_pickup_and_writes_audit_entry(admin_client, admin_user, pickup):
    response = admin_client.post(reverse("site_admin:order_delete"), {"item_delete_id": pickup.pk})
    assert response.status_code == 302
    assert not Pickup.objects.filter(pk=pickup.pk).exists()
    entry = AuditLog.objects.get(action="pickup_deleted")
    assert entry.actor == admin_user
    assert entry.target_id == str(pickup.pickup_id)
    assert entry.snapshot["customer_phone"] == pickup.customer.phone
    assert entry.snapshot["items"][0]["item"] == "Paper"


@pytest.mark.django_db
def test_order_delete_with_unknown_id_changes_nothing(admin_client, pickup):
    response = admin_client.post(reverse("site_admin:order_delete"), {"item_delete_id": "not-a-uuid"})
    assert response.status_code == 302
    assert Pickup.objects.filter(pk=pickup.pk).exists()
    assert not AuditLog.objects.exists()


@pytest.mark.django_db
def test_customer_cannot_delete_orders(customer_client, pickup):
    response = customer_client.post(reverse("site_admin:order_delete"), {"item_delete_id": pickup.pk})
    assert response.status_code == 403
    assert Pickup.objects.filter(pk=pickup.pk).exists()


@pytest.mark.django_db
def test_top_items_use_actual_figures_and_fall_back_to_estimates(pickup, paper, metal):
    paper_row = PickupItems.objects.get(pickup=pickup, item=paper)
    paper_row.actual_quantity = Decimal("3.00")
    paper_row.final_price = Decimal("15.00")
    paper_row.save()
    PickupItems.objects.create(pickup=pickup, item=metal, quantity=Decimal("1.000"))
    pickup.status = "Picked-up"
    pickup.save()

    ranking = top_items_by_value()

    assert [row["name"] for row in ranking] == ["Paper", "Metal"]
    assert ranking[0]["total"] == Decimal("45.00")
    assert ranking[1]["total"] == Decimal("20.00")


@pytest.mark.django_db
def test_top_items_ignore_orders_that_are_not_picked_up(pickup):
    assert top_items_by_value() == []


@pytest.mark.django_db
def test_top_items_respect_the_limit(pickup, paper, metal):
    PickupItems.objects.create(pickup=pickup, item=metal, quantity=Decimal("1.000"))
    pickup.status = "Picked-up"
    pickup.save()
    assert len(top_items_by_value(limit=1)) == 1
