from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from common_models.models import Pickup
from notifications.models import Notifications, Recipients


def make_pickups(customer, city, count):
    day = timezone.localdate() + timedelta(days=1)
    return [
        Pickup.objects.create(
            customer=customer,
            status="Requested",
            pickup_date=day,
            address="Street 1",
            city=city,
            state=city.state,
            pin_code="160055",
        )
        for _ in range(count)
    ]


def make_notifications(user, count):
    rows = []
    for n in range(count):
        notification = Notifications.objects.create(
            sent_to="Customer", subject=f"Update {n:02d}", content=f"Body {n}", url="/x"
        )
        rows.append(Recipients.objects.create(notification=notification, recipient=user))
    return rows


@pytest.mark.django_db
def test_history_page_two_is_served_from_the_url(customer_client, customer, city):
    make_pickups(customer, city, 12)
    response = customer_client.get(reverse("customer:history"), {"page": 2})
    assert response.status_code == 200
    assert response.context["page_obj"].number == 2
    assert len(response.context["pickup_list"]) == 2


@pytest.mark.django_db
def test_history_default_page_shows_ten_rows(customer_client, customer, city):
    make_pickups(customer, city, 12)
    response = customer_client.get(reverse("customer:history"))
    assert response.context["page_obj"].number == 1
    assert len(response.context["pickup_list"]) == 10
    assert response.context["total_count"] == 12


@pytest.mark.django_db
def test_history_header_shows_the_overall_total(customer_client, customer, city):
    make_pickups(customer, city, 12)
    response = customer_client.get(reverse("customer:history"), {"page": 2})
    assert "12 requests so far" in response.content.decode()


@pytest.mark.django_db
def test_history_shows_pager_links_only_when_needed(customer_client, customer, city):
    make_pickups(customer, city, 3)
    assert 'class="pagination' not in customer_client.get(reverse("customer:history")).content.decode()
    make_pickups(customer, city, 9)
    html = customer_client.get(reverse("customer:history")).content.decode()
    assert 'class="pagination' in html
    assert "?page=2" in html


@pytest.mark.django_db
def test_history_out_of_range_page_shows_last_page(customer_client, customer, city):
    make_pickups(customer, city, 12)
    response = customer_client.get(reverse("customer:history"), {"page": 99})
    assert response.context["page_obj"].number == 2


@pytest.mark.django_db
def test_history_only_lists_the_customers_own_requests(
    customer_client, customer, other_customer, city
):
    make_pickups(customer, city, 2)
    make_pickups(other_customer, city, 5)
    response = customer_client.get(reverse("customer:history"))
    assert response.context["total_count"] == 2


@pytest.mark.django_db
def test_history_ignores_search_parameter(customer_client, customer, city):
    make_pickups(customer, city, 3)
    response = customer_client.get(reverse("customer:history"), {"q": "nothing"})
    assert response.context["total_count"] == 3
    assert response.context["search"] == ""


@pytest.mark.django_db
def test_history_empty_state_for_new_customers(customer_client):
    response = customer_client.get(reverse("customer:history"))
    assert response.status_code == 200
    assert "No requests yet" in response.content.decode()


@pytest.mark.django_db
def test_notifications_are_paginated_from_the_url(customer_client, customer):
    make_notifications(customer, 12)
    response = customer_client.get(reverse("customer:notifications"), {"page": 2})
    assert response.status_code == 200
    assert response.context["page_obj"].number == 2
    assert len(response.context["notif_list"]) == 2


@pytest.mark.django_db
def test_notifications_only_mark_the_visible_page_as_read(customer_client, customer):
    make_notifications(customer, 12)
    customer_client.get(reverse("customer:notifications"))
    assert Recipients.objects.filter(recipient=customer, read=False).count() == 2
    customer_client.get(reverse("customer:notifications"), {"page": 2})
    assert Recipients.objects.filter(recipient=customer, read=False).count() == 0


@pytest.mark.django_db
def test_notifications_only_show_the_customers_own(customer_client, customer, other_customer):
    make_notifications(customer, 2)
    make_notifications(other_customer, 5)
    response = customer_client.get(reverse("customer:notifications"))
    assert response.context["total_count"] == 2


@pytest.mark.django_db
def test_notifications_empty_state(customer_client):
    response = customer_client.get(reverse("customer:notifications"))
    assert "You are all caught up" in response.content.decode()
