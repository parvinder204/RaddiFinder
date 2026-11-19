from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from common_models.models import Item, PickupBoy, ReferenceCounter
from common_models.models.reference_models import next_reference
from common_models.services import create_pickup_request


def make_item(name="Paper"):
    return Item.objects.create(name=name, unit="Kg", description="d", price=Decimal("1.00"))


@pytest.mark.django_db
def test_items_get_sequential_prod_references():
    first = make_item("A")
    second = make_item("B")
    assert first.reference == "PROD_1"
    assert second.reference == "PROD_2"


@pytest.mark.django_db
def test_each_model_has_its_own_prefix_and_counter(pickup, paper):
    boy = PickupBoy.objects.create(full_name="Ravi", phone="9000000001")
    assert pickup.reference == "PKRQ_1"
    assert boy.reference == "SRPB_1"
    assert paper.reference == "PROD_1"
    assert make_item().reference == "PROD_2"


@pytest.mark.django_db
def test_reference_is_kept_when_the_row_is_saved_again():
    item = make_item()
    item.name = "Renamed"
    item.save()
    item.refresh_from_db()
    assert item.reference == "PROD_1"
    item.save(update_fields=["name"])
    item.refresh_from_db()
    assert item.reference == "PROD_1"


@pytest.mark.django_db
def test_deleted_numbers_are_not_reused():
    make_item("A")
    second = make_item("B")
    second.delete()
    assert make_item("C").reference == "PROD_3"


@pytest.mark.django_db
def test_an_explicit_reference_is_respected():
    item = Item(name="Legacy", unit="Kg", description="d", price=Decimal("1.00"), reference="PROD_99")
    item.save()
    assert Item.objects.get(pk=item.pk).reference == "PROD_99"


@pytest.mark.django_db
def test_primary_keys_stay_uuids(pickup):
    assert str(pickup.pickup_id) != pickup.reference
    assert len(str(pickup.pickup_id)) == 36
    assert type(pickup.pk) is type(pickup.pickup_id)


@pytest.mark.django_db
def test_next_reference_advances_the_counter():
    assert next_reference("TEST") == "TEST_1"
    assert next_reference("TEST") == "TEST_2"
    assert ReferenceCounter.objects.get(prefix="TEST").last_value == 2


@pytest.mark.django_db
def test_pickup_str_uses_the_reference(pickup):
    assert str(pickup) == pickup.reference


@pytest.mark.django_db
def test_requests_created_through_the_service_get_references(customer, city, paper):
    pickup = create_pickup_request(
        customer=customer,
        pickup_date=(timezone.localdate() + timedelta(days=1)).isoformat(),
        time_slot="9-10",
        notes="",
        address="Street 1",
        state_id=str(city.state_id),
        city_id=str(city.id),
        pin_code="160055",
        raw_items=[{"id": str(paper.id), "quantity": "2"}],
    )
    assert pickup.reference.startswith("PKRQ_")


@pytest.mark.django_db
def test_references_are_unique_across_rows():
    references = {make_item(f"Item {n}").reference for n in range(5)}
    assert len(references) == 5
