from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.test import Client
from django.utils import timezone

from accounts.models import Person
from common_models.models import City, Item, Pickup, PickupItems, State

MODEL_BACKEND = "django.contrib.auth.backends.ModelBackend"


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def default_lead_days(settings):
    settings.PICKUP_MIN_LEAD_DAYS = 1


@pytest.fixture
def state(db):
    return State.objects.create(name="Punjab")


@pytest.fixture
def city(state):
    return City.objects.create(state=state, name="Mohali", available=True)


@pytest.fixture
def closed_city(state):
    return City.objects.create(state=state, name="Ropar", available=False)


@pytest.fixture
def customer(db):
    return Person.objects.create_user(
        password="StrongPass#123", phone="9876543210", role="Customer"
    )


@pytest.fixture
def other_customer(db):
    return Person.objects.create_user(
        password="StrongPass#123", phone="9876543211", role="Customer"
    )


@pytest.fixture
def admin_user(db):
    user = Person.objects.create(phone="9123456780", role="Admin", is_staff=True)
    user.set_password("StrongPass#123")
    user.save()
    return user


@pytest.fixture
def paper(db):
    return Item.objects.create(
        name="Paper", unit="Kg", description="Newspaper", price=Decimal("10.00")
    )


@pytest.fixture
def metal(db):
    return Item.objects.create(
        name="Metal", unit="Kg", description="Iron", price=Decimal("20.00")
    )


@pytest.fixture
def pickup(customer, city, paper):
    order = Pickup.objects.create(
        customer=customer,
        status="Requested",
        pickup_date=timezone.localdate() + timedelta(days=1),
        address="Street 1",
        city=city,
        state=city.state,
        pin_code="160055",
    )
    PickupItems.objects.create(pickup=order, item=paper, quantity=Decimal("2.000"))
    return order


@pytest.fixture
def admin_client(admin_user):
    client = Client()
    client.force_login(admin_user, backend=MODEL_BACKEND)
    return client


@pytest.fixture
def customer_client(customer):
    client = Client()
    client.force_login(customer, backend=MODEL_BACKEND)
    return client
