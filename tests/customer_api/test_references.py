import pytest

from customer_api.serializer import HistoryListSerializer, ViewOrderListSerializer


@pytest.mark.django_db
def test_history_serializer_exposes_the_reference_and_the_uuid(pickup):
    data = HistoryListSerializer(pickup).data
    assert data["reference"] == pickup.reference
    assert data["pickup_id"] == str(pickup.pickup_id)


@pytest.mark.django_db
def test_order_serializer_exposes_the_reference(pickup):
    data = ViewOrderListSerializer(pickup).data
    assert data["reference"] == pickup.reference
    assert data["pickup_id"] == str(pickup.pickup_id)
