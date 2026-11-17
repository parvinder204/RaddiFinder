from decimal import Decimal
from urllib.parse import parse_qs, urlparse

import pytest
from django.db.models import Q
from django.test import RequestFactory

from common_models.models import Item
from site_admin.pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_SEARCH_LENGTH,
    list_context,
    paginate,
    parse_page_number,
    parse_page_size,
    parse_search,
    preserved_query,
    redirect_to_list,
)

factory = RequestFactory()


def make_items(count, prefix="Item"):
    Item.objects.bulk_create(
        [
            Item(name=f"{prefix} {n:02d}", unit="Kg", description="desc", price=Decimal("1.00"))
            for n in range(count)
        ]
    )


def get(**params):
    return factory.get("/list", params)


@pytest.mark.parametrize(
    ("value", "expected"),
    [("25", 25), ("100", 100), ("7", 10), ("abc", 10), ("", 10), ("-5", 10), ("0", 10)],
)
def test_parse_page_size(value, expected):
    assert parse_page_size({"per_page": value}) == expected


def test_parse_page_size_defaults_when_missing():
    assert parse_page_size({}) == DEFAULT_PAGE_SIZE


@pytest.mark.parametrize(
    ("value", "expected"), [("3", 3), ("1", 1), ("0", 1), ("-4", 1), ("abc", 1), ("", 1)]
)
def test_parse_page_number(value, expected):
    assert parse_page_number({"page": value}) == expected


def test_parse_search_collapses_whitespace():
    assert parse_search({"q": "  paper   blue  "}) == "paper blue"


def test_parse_search_is_length_limited():
    assert len(parse_search({"q": "a" * 500})) == MAX_SEARCH_LENGTH


@pytest.mark.django_db
def test_paginate_returns_first_page_by_default():
    make_items(25)
    result = paginate(get(), Item.objects.order_by("name"))
    assert result.page.number == 1
    assert len(result.page.object_list) == 10
    assert result.page.paginator.num_pages == 3


@pytest.mark.django_db
def test_paginate_uses_requested_page_and_size():
    make_items(25)
    result = paginate(get(page="2", per_page="25"), Item.objects.order_by("name"))
    assert result.page.number == 1
    assert len(result.page.object_list) == 25


@pytest.mark.django_db
def test_paginate_returns_requested_page():
    make_items(25)
    result = paginate(get(page="3"), Item.objects.order_by("name"))
    assert result.page.number == 3
    assert [item.name for item in result.page.object_list] == [f"Item {n:02d}" for n in range(20, 25)]


@pytest.mark.django_db
@pytest.mark.parametrize("page", ["99", "0", "-1", "abc"])
def test_paginate_clamps_bad_page_numbers(page):
    make_items(25)
    result = paginate(get(page=page), Item.objects.order_by("name"))
    expected = 3 if page == "99" else 1
    assert result.page.number == expected


@pytest.mark.django_db
def test_paginate_handles_empty_queryset():
    result = paginate(get(), Item.objects.order_by("name"))
    assert result.page.number == 1
    assert list(result.page.object_list) == []


@pytest.mark.django_db
def test_search_filters_by_field():
    make_items(3, prefix="Paper")
    make_items(2, prefix="Metal")
    result = paginate(get(q="metal"), Item.objects.order_by("name"), search_fields=("name",))
    assert [item.name for item in result.page.object_list] == ["Metal 00", "Metal 01"]


@pytest.mark.django_db
def test_search_requires_every_word_to_match():
    make_items(3, prefix="Paper")
    result = paginate(get(q="paper 01"), Item.objects.order_by("name"), search_fields=("name",))
    assert [item.name for item in result.page.object_list] == ["Paper 01"]


@pytest.mark.django_db
def test_search_matches_any_listed_field():
    Item.objects.create(name="Copper", unit="Kg", description="wire", price=Decimal("5.00"))
    Item.objects.create(name="Glass", unit="Kg", description="bottles", price=Decimal("2.00"))
    result = paginate(
        get(q="wire"), Item.objects.order_by("name"), search_fields=("name", "description")
    )
    assert [item.name for item in result.page.object_list] == ["Copper"]


@pytest.mark.django_db
def test_extra_search_clause_is_applied():
    make_items(3, prefix="Paper")
    result = paginate(
        get(q="zzz"),
        Item.objects.order_by("name"),
        search_fields=("name",),
        extra_search=lambda word: Q(name="Paper 02"),
    )
    assert [item.name for item in result.page.object_list] == ["Paper 02"]


@pytest.mark.django_db
def test_search_with_no_matches_returns_empty_page():
    make_items(3)
    result = paginate(get(q="nothing"), Item.objects.order_by("name"), search_fields=("name",))
    assert result.page.paginator.count == 0


@pytest.mark.django_db
def test_list_context_omits_default_values_from_links():
    make_items(25)
    context = list_context(paginate(get(), Item.objects.order_by("name")))
    assert context["list_query"] == ""
    assert context["current_query"] == ""
    assert context["total_count"] == 25
    assert context["first_index"] == 1
    assert context["last_index"] == 10


@pytest.mark.django_db
def test_list_context_keeps_search_size_and_page_in_links():
    make_items(60, prefix="Paper")
    request = get(q="paper", per_page="25", page="2")
    context = list_context(paginate(request, Item.objects.order_by("name"), search_fields=("name",)))
    assert parse_qs(context["list_query"]) == {"q": ["paper"], "per_page": ["25"]}
    assert parse_qs(context["current_query"]) == {"q": ["paper"], "per_page": ["25"], "page": ["2"]}
    assert context["first_index"] == 26
    assert context["last_index"] == 50


@pytest.mark.django_db
def test_list_context_reports_the_clamped_page():
    make_items(25)
    context = list_context(paginate(get(page="99"), Item.objects.order_by("name")))
    assert parse_qs(context["current_query"]) == {"page": ["3"]}


@pytest.mark.django_db
def test_list_context_elides_long_page_ranges():
    make_items(200)
    context = list_context(paginate(get(page="10"), Item.objects.order_by("name")))
    assert context["ellipsis"] in context["page_links"]
    assert 10 in context["page_links"]
    assert 1 in context["page_links"]
    assert 20 in context["page_links"]


def test_preserved_query_keeps_only_known_params():
    request = get(q="paper", page="2", per_page="25", other="x", empty="")
    assert parse_qs(preserved_query(request)) == {"q": ["paper"], "per_page": ["25"], "page": ["2"]}


def test_preserved_query_is_empty_without_state():
    assert preserved_query(get()) == ""


@pytest.mark.django_db
def test_redirect_to_list_carries_state_forward():
    response = redirect_to_list(get(q="a b", page="3"), "site_admin:manage-products")
    parsed = urlparse(response.url)
    assert response.status_code == 302
    assert parsed.path.endswith("/manage-products")
    assert parse_qs(parsed.query) == {"q": ["a b"], "page": ["3"]}


@pytest.mark.django_db
def test_redirect_to_list_without_state_has_no_query_string():
    response = redirect_to_list(get(), "site_admin:manage-products")
    assert "?" not in response.url
