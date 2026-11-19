import pytest
from django.urls import reverse
from django.utils import timezone


@pytest.mark.django_db
def test_customer_pages_use_the_shared_layout(customer_client):
    html = customer_client.get(reverse("customer:select-items")).content.decode()
    assert 'class="rf-navbar"' in html
    assert 'id="menu"' in html
    assert 'id="profile"' in html
    assert 'class="rf-footer"' in html
    assert "css/theme.css" in html
    assert "customer/css/modern.css" in html
    assert "js/calendar-picker.js" in html


@pytest.mark.django_db
def test_sidebars_can_be_closed(customer_client):
    html = customer_client.get(reverse("customer:select-items")).content.decode()
    assert html.count('data-bs-dismiss="offcanvas"') == 2
    assert "offcanvasRight" not in html


@pytest.mark.django_db
def test_footer_shows_the_copyright_label(customer_client):
    html = customer_client.get(reverse("customer:select-items")).content.decode()
    assert f"© {timezone.localdate().year} RaddiFinder. All rights reserved." in html


@pytest.mark.django_db
def test_logout_stays_in_the_profile_panel(customer_client):
    html = customer_client.get(reverse("customer:select-items")).content.decode()
    assert reverse("accounts:logout") in html
    assert "Logout" in html


@pytest.mark.django_db
def test_product_grid_wraps_the_items(customer_client, paper, metal):
    html = customer_client.get(reverse("customer:select-items")).content.decode()
    assert 'class="product-grid"' in html
    assert html.count('class="product-grid__item"') == 2


@pytest.mark.django_db
def test_date_field_is_present_for_the_calendar(customer_client):
    html = customer_client.get(reverse("customer:select-items")).content.decode()
    assert 'type="date"' in html


@pytest.mark.django_db
def test_navbar_marks_the_current_page(customer_client):
    html = customer_client.get(reverse("customer:history")).content.decode()
    assert 'aria-current="page"' in html


def test_message_alerts_sit_above_the_sticky_navbar():
    from django.contrib.staticfiles import finders

    css = open(finders.find("customer/css/modern.css")).read()
    assert ".rf-site .alert-style" in css
    assert "z-index: 1060" in css


@pytest.mark.django_db
def test_footer_only_shows_the_copyright_line(customer_client):
    html = customer_client.get(reverse("customer:select-items")).content.decode()
    footer = html.split('class="rf-footer"', 1)[1].split("</footer>", 1)[0]
    assert "All rights reserved." in footer
    assert "Quick links" not in footer
    assert "Contact" not in footer
    assert "<img" not in footer


@pytest.mark.django_db
def test_custom_dropdown_assets_are_loaded(customer_client):
    html = customer_client.get(reverse("customer:select-items")).content.decode()
    assert "css/select-picker.css" in html
    assert "js/select-picker.js" in html


@pytest.mark.django_db
def test_signed_out_visitors_only_see_the_home_link():
    from django.test import Client

    html = Client().get(reverse("customer:select-items")).content.decode()
    assert reverse("customer:dashboard") in html
    assert reverse("customer:history") not in html
    assert reverse("customer:notifications") not in html
    assert reverse("customer:account-settings") not in html
    assert 'id="profile"' not in html


@pytest.mark.django_db
def test_signed_out_visitors_see_the_login_button():
    from django.test import Client

    html = Client().get(reverse("customer:select-items")).content.decode()
    assert reverse("customer:phone-number") in html
    assert "rf-avatar" not in html


@pytest.mark.django_db
def test_signed_in_customers_see_every_link(customer_client):
    html = customer_client.get(reverse("customer:select-items")).content.decode()
    assert reverse("customer:history") in html
    assert reverse("customer:notifications") in html
    assert reverse("customer:account-settings") in html
    assert "rf-avatar" in html


@pytest.mark.django_db
def test_customer_pager_uses_angle_bracket_buttons(customer_client, customer, city):
    from tests.customer_app.test_list_views import make_pickups

    make_pickups(customer, city, 12)
    html = customer_client.get(reverse("customer:history")).content.decode()
    assert 'aria-label="Next page"' in html
    assert "&gt;" in html
    assert ">Next<" not in html


@pytest.mark.django_db
def test_booking_page_loads_the_draft_script_and_restores_by_default():
    from django.test import Client

    html = Client().get(reverse("customer:select-items")).content.decode()
    assert "customer/js/wizard-draft.js" in html
    assert "RaddiWizard.start" in html
    assert "authenticated: false" in html
    assert "restore: true" in html


@pytest.mark.django_db
def test_booking_page_passes_the_signed_in_customer_to_the_draft(customer_client, customer):
    html = customer_client.get(reverse("customer:select-items")).content.decode()
    assert "authenticated: true" in html
    assert f'userId: "{customer.pk}"' in html


@pytest.mark.django_db
def test_server_side_selection_takes_priority_over_the_saved_draft(customer_client, paper):
    html = customer_client.post(
        reverse("customer:select-items"), {"product_id": str(paper.id), "step_out": ""}
    ).content.decode()
    assert "restore: false" in html
    assert "$('#step-btn-3').click()" in html
    assert str(paper.id) in html


@pytest.mark.django_db
def test_booking_page_clears_the_draft_when_the_request_is_placed(customer_client):
    html = customer_client.get(reverse("customer:select-items")).content.decode()
    assert "RaddiWizard.finish()" in html
