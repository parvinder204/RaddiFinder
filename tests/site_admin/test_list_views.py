from datetime import timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.models import Person
from common_models.models import City, Item, Pickup, PickupBoy
from notifications.models import Notifications, Recipients


def make_pickups(customer, city, count, status="Requested"):
    day = timezone.localdate() + timedelta(days=1)
    return [
        Pickup.objects.create(
            customer=customer,
            status=status,
            pickup_date=day,
            address="Street 1",
            city=city,
            state=city.state,
            pin_code="160055",
        )
        for _ in range(count)
    ]


def make_boys(count):
    return [
        PickupBoy.objects.create(full_name=f"Boy {n:02d}", phone=f"90000000{n:02d}")
        for n in range(count)
    ]


def make_items(count):
    return [
        Item.objects.create(
            name=f"Item {n:02d}", unit="Kg", description="desc", price=Decimal("1.00")
        )
        for n in range(count)
    ]


def make_cities(state, count):
    return [City.objects.create(state=state, name=f"City {n:02d}", available=True) for n in range(count)]


def make_notifications(user, count, subject="Alpha"):
    rows = []
    for n in range(count):
        notification = Notifications.objects.create(
            sent_to="Admin", subject=f"{subject} {n:02d}", content=f"Body {n}", url="/x"
        )
        rows.append(Recipients.objects.create(notification=notification, recipient=user))
    return rows


def redirected_query(response):
    return parse_qs(urlparse(response.url).query)


@pytest.mark.django_db
def test_requests_page_two_is_served_from_the_url(admin_client, customer, city):
    make_pickups(customer, city, 12)
    response = admin_client.get(reverse("site_admin:manage-requests"), {"page": 2})
    assert response.status_code == 200
    assert response.context["page_obj"].number == 2
    assert len(response.context["pickup_list"]) == 2
    assert response.context["first_index"] == 11


@pytest.mark.django_db
def test_requests_default_page_shows_ten_rows(admin_client, customer, city):
    make_pickups(customer, city, 12)
    response = admin_client.get(reverse("site_admin:manage-requests"))
    assert response.context["page_obj"].number == 1
    assert len(response.context["pickup_list"]) == 10


@pytest.mark.django_db
def test_requests_page_size_comes_from_the_url(admin_client, customer, city):
    make_pickups(customer, city, 12)
    response = admin_client.get(reverse("site_admin:manage-requests"), {"per_page": 25})
    assert len(response.context["pickup_list"]) == 12
    assert response.context["page_size"] == 25


@pytest.mark.django_db
def test_requests_out_of_range_page_shows_last_page(admin_client, customer, city):
    make_pickups(customer, city, 12)
    response = admin_client.get(reverse("site_admin:manage-requests"), {"page": 99})
    assert response.context["page_obj"].number == 2


@pytest.mark.django_db
def test_requests_pager_links_keep_the_search(admin_client, customer, city):
    customer.first_name = "Asha"
    customer.save()
    make_pickups(customer, city, 12)
    response = admin_client.get(reverse("site_admin:manage-requests"), {"q": "asha"})
    assert response.status_code == 200
    assert response.context["total_count"] == 12
    assert "?q=asha&page=2" in response.content.decode()


@pytest.mark.django_db
def test_requests_search_by_customer_name(admin_client, customer, other_customer, city):
    customer.first_name = "Asha"
    customer.save()
    other_customer.first_name = "Zed"
    other_customer.save()
    make_pickups(customer, city, 3)
    make_pickups(other_customer, city, 2)
    response = admin_client.get(reverse("site_admin:manage-requests"), {"q": "zed"})
    assert response.context["total_count"] == 2


@pytest.mark.django_db
def test_requests_search_by_phone(admin_client, customer, other_customer, city):
    make_pickups(customer, city, 3)
    make_pickups(other_customer, city, 2)
    response = admin_client.get(reverse("site_admin:manage-requests"), {"q": other_customer.phone})
    assert response.context["total_count"] == 2


@pytest.mark.django_db
def test_requests_search_by_order_id(admin_client, customer, city):
    orders = make_pickups(customer, city, 3)
    response = admin_client.get(reverse("site_admin:manage-requests"), {"q": str(orders[1].pickup_id)})
    assert [p.pickup_id for p in response.context["pickup_list"]] == [orders[1].pickup_id]


@pytest.mark.django_db
def test_requests_search_by_status_word(admin_client, customer, city):
    make_pickups(customer, city, 2, status="Requested")
    make_pickups(customer, city, 3, status="Cancelled")
    response = admin_client.get(reverse("site_admin:manage-requests"), {"q": "cancel"})
    assert response.context["total_count"] == 3
    response = admin_client.get(reverse("site_admin:manage-requests"), {"q": "raised"})
    assert response.context["total_count"] == 2


@pytest.mark.django_db
def test_requests_search_by_pickup_date(admin_client, customer, city):
    make_pickups(customer, city, 2)
    other = make_pickups(customer, city, 1)[0]
    other.pickup_date = timezone.localdate() + timedelta(days=5)
    other.save()
    text = other.pickup_date.strftime("%d-%m-%Y")
    response = admin_client.get(reverse("site_admin:manage-requests"), {"q": text})
    assert [p.pickup_id for p in response.context["pickup_list"]] == [other.pickup_id]


@pytest.mark.django_db
def test_requests_with_no_match_show_empty_state(admin_client, customer, city):
    make_pickups(customer, city, 2)
    response = admin_client.get(reverse("site_admin:manage-requests"), {"q": "nomatch"})
    assert response.context["total_count"] == 0
    assert "No matching entries found" in response.content.decode()


@pytest.mark.django_db
def test_requests_delete_returns_to_the_same_page(admin_client, customer, city):
    orders = make_pickups(customer, city, 12)
    url = reverse("site_admin:order_delete") + "?page=2"
    response = admin_client.post(url, {"item_delete_id": orders[0].pickup_id})
    assert response.status_code == 302
    assert redirected_query(response) == {"page": ["2"]}
    assert not Pickup.objects.filter(pk=orders[0].pk).exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name", ["manage-requests", "manage-pickup-boy", "manage-products", "notifications"]
)
def test_list_pages_redirect_customers_away(customer_client, name):
    response = customer_client.get(reverse(f"site_admin:{name}"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_service_area_page_forbids_customers(customer_client):
    response = customer_client.get(reverse("site_admin:avail_city"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_pickup_boys_are_paginated_and_searchable(admin_client):
    make_boys(12)
    page = admin_client.get(reverse("site_admin:manage-pickup-boy"), {"page": 2})
    assert page.context["page_obj"].number == 2
    assert len(page.context["pickupboy_list"]) == 2
    search = admin_client.get(reverse("site_admin:manage-pickup-boy"), {"q": "Boy 07"})
    assert [b.full_name for b in search.context["pickupboy_list"]] == ["Boy 07"]
    by_phone = admin_client.get(reverse("site_admin:manage-pickup-boy"), {"q": "9000000003"})
    assert [b.full_name for b in by_phone.context["pickupboy_list"]] == ["Boy 03"]


@pytest.mark.django_db
def test_pickup_boy_list_hides_unemployed(admin_client):
    boys = make_boys(3)
    boys[0].employed = False
    boys[0].save()
    response = admin_client.get(reverse("site_admin:manage-pickup-boy"))
    assert response.context["total_count"] == 2


@pytest.mark.django_db
def test_pickup_boy_delete_returns_to_the_same_page(admin_client):
    boys = make_boys(12)
    url = reverse("site_admin:manage-pickup-boy") + "?q=Boy&page=2"
    response = admin_client.post(url, {"delete_submit": "1", "delete_id": boys[0].pk})
    assert response.status_code == 302
    assert redirected_query(response) == {"q": ["Boy"], "page": ["2"]}
    boys[0].refresh_from_db()
    assert boys[0].employed is False


@pytest.mark.django_db
def test_products_are_paginated_and_searchable(admin_client):
    make_items(12)
    page = admin_client.get(reverse("site_admin:manage-products"), {"page": 2})
    assert page.context["page_obj"].number == 2
    assert len(page.context["item_list"]) == 2
    search = admin_client.get(reverse("site_admin:manage-products"), {"q": "Item 05"})
    assert [i.name for i in search.context["item_list"]] == ["Item 05"]


@pytest.mark.django_db
def test_products_search_matches_description_and_price(admin_client):
    Item.objects.create(name="Copper", unit="Kg", description="bare wire", price=Decimal("415.50"))
    Item.objects.create(name="Glass", unit="Kg", description="bottles", price=Decimal("2.00"))
    by_description = admin_client.get(reverse("site_admin:manage-products"), {"q": "wire"})
    assert [i.name for i in by_description.context["item_list"]] == ["Copper"]
    by_price = admin_client.get(reverse("site_admin:manage-products"), {"q": "415"})
    assert [i.name for i in by_price.context["item_list"]] == ["Copper"]


@pytest.mark.django_db
def test_product_delete_returns_to_the_same_page(admin_client):
    items = make_items(12)
    url = reverse("site_admin:manage-products") + "?page=2"
    response = admin_client.post(url, {"delete_submit": "1", "delete_id": items[0].pk})
    assert response.status_code == 302
    assert redirected_query(response) == {"page": ["2"]}
    assert not Item.objects.filter(pk=items[0].pk).exists()


@pytest.mark.django_db
def test_service_areas_are_paginated_and_numbered(admin_client, state):
    make_cities(state, 12)
    response = admin_client.get(reverse("site_admin:avail_city"), {"page": 2})
    assert response.status_code == 200
    assert [c.name for c in response.context["avail_city"]] == ["City 10", "City 11"]
    assert response.context["first_index"] == 11


@pytest.mark.django_db
def test_service_areas_search_by_city_or_state(admin_client, state):
    make_cities(state, 3)
    by_city = admin_client.get(reverse("site_admin:avail_city"), {"q": "city 01"})
    assert [c.name for c in by_city.context["avail_city"]] == ["City 01"]
    by_state = admin_client.get(reverse("site_admin:avail_city"), {"q": "punjab"})
    assert by_state.context["total_count"] == 3


@pytest.mark.django_db
def test_service_areas_hide_unavailable_cities(admin_client, state, closed_city):
    make_cities(state, 2)
    response = admin_client.get(reverse("site_admin:avail_city"))
    assert response.context["total_count"] == 2


@pytest.mark.django_db
def test_removing_a_service_area_returns_to_the_same_page(admin_client, state):
    cities = make_cities(state, 12)
    url = reverse("site_admin:avail_city_del", kwargs={"del_pk": cities[0].pk}) + "?page=2"
    response = admin_client.get(url)
    assert response.status_code == 302
    assert urlparse(response.url).path == reverse("site_admin:avail_city")
    assert redirected_query(response) == {"page": ["2"]}
    cities[0].refresh_from_db()
    assert cities[0].available is False


@pytest.mark.django_db
def test_adding_a_service_area_redirects_to_the_list(admin_client, state, closed_city):
    response = admin_client.post(reverse("site_admin:avail_city"), {"city_id": closed_city.pk})
    assert response.status_code == 302
    closed_city.refresh_from_db()
    assert closed_city.available is True


@pytest.mark.django_db
def test_notifications_are_paginated_from_the_url(admin_client, admin_user):
    make_notifications(admin_user, 12)
    response = admin_client.get(reverse("site_admin:notifications"), {"page": 2})
    assert response.status_code == 200
    assert response.context["page_obj"].number == 2
    assert len(response.context["notif_list"]) == 2


@pytest.mark.django_db
def test_notifications_only_mark_the_visible_page_as_read(admin_client, admin_user):
    make_notifications(admin_user, 12)
    admin_client.get(reverse("site_admin:notifications"))
    assert Recipients.objects.filter(recipient=admin_user, read=False).count() == 2
    admin_client.get(reverse("site_admin:notifications"), {"page": 2})
    assert Recipients.objects.filter(recipient=admin_user, read=False).count() == 0


@pytest.mark.django_db
def test_notifications_search_by_subject_or_content(admin_client, admin_user):
    make_notifications(admin_user, 3, subject="Alpha")
    make_notifications(admin_user, 2, subject="Beta")
    by_subject = admin_client.get(reverse("site_admin:notifications"), {"q": "beta"})
    assert by_subject.context["total_count"] == 2
    by_content = admin_client.get(reverse("site_admin:notifications"), {"q": "body 1"})
    assert by_content.context["total_count"] == 2


@pytest.mark.django_db
def test_notifications_only_show_the_admins_own(admin_client, admin_user, customer):
    make_notifications(admin_user, 2)
    make_notifications(customer, 5)
    response = admin_client.get(reverse("site_admin:notifications"))
    assert response.context["total_count"] == 2
