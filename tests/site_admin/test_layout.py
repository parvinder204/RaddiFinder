import pytest
from django.urls import reverse
from django.utils import timezone


@pytest.mark.django_db
def test_admin_layout_has_sidebar_toggle_and_logo(admin_client):
    html = admin_client.get(reverse("site_admin:manage-products")).content.decode()
    assert 'id="vertical-menu-btn"' in html
    assert "images/logo.png" in html
    assert "css/theme.css" in html
    assert "css/admin-modern.css" in html


@pytest.mark.django_db
def test_admin_footer_shows_the_copyright_label(admin_client):
    html = admin_client.get(reverse("site_admin:manage-products")).content.decode()
    assert f"© {timezone.localdate().year} RaddiFinder. All rights reserved." in html


@pytest.mark.django_db
def test_admin_keeps_the_logout_dropdown(admin_client):
    html = admin_client.get(reverse("site_admin:manage-products")).content.decode()
    assert "dropdown-menu" in html
    assert "Logout" in html


@pytest.mark.django_db
def test_admin_pages_no_longer_load_datatables_scripts(admin_client):
    html = admin_client.get(reverse("site_admin:manage-products")).content.decode()
    assert "jquery.dataTables" not in html


@pytest.mark.django_db
def test_admin_loads_the_custom_dropdown_assets(admin_client):
    html = admin_client.get(reverse("site_admin:manage-products")).content.decode()
    assert "css/select-picker.css" in html
    assert "js/select-picker.js" in html
    assert "js/waves-shim.js" in html


@pytest.mark.django_db
def test_list_pages_use_the_single_row_toolbar_and_compact_pager(admin_client):
    html = admin_client.get(reverse("site_admin:manage-products")).content.decode()
    assert 'class="js-list-controls list-toolbar"' in html
    assert "list-toolbar__search" in html
    assert 'class="list-footer"' in html
    assert 'aria-label="Next page"' in html
    assert "&lt;" in html
    assert "&gt;" in html
    assert "Previous<" not in html
    assert "css/list-controls.css" in html
