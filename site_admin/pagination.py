from dataclasses import dataclass
from urllib.parse import urlencode

from django.core.paginator import Page, Paginator
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse

PAGE_SIZES = (10, 25, 50, 100)
DEFAULT_PAGE_SIZE = 10
MAX_SEARCH_LENGTH = 100
MAX_SEARCH_TERMS = 5
SEARCH_PARAM = "q"
SIZE_PARAM = "per_page"
PAGE_PARAM = "page"
STATE_PARAMS = (SEARCH_PARAM, SIZE_PARAM, PAGE_PARAM)


@dataclass(frozen=True)
class ListPage:
    page: Page
    search: str
    page_size: int


def parse_page_size(params):
    try:
        size = int(params.get(SIZE_PARAM, ""))
    except (TypeError, ValueError):
        return DEFAULT_PAGE_SIZE
    return size if size in PAGE_SIZES else DEFAULT_PAGE_SIZE


def parse_page_number(params):
    try:
        number = int(params.get(PAGE_PARAM, ""))
    except (TypeError, ValueError):
        return 1
    return max(number, 1)


def parse_search(params):
    return " ".join(params.get(SEARCH_PARAM, "").split())[:MAX_SEARCH_LENGTH]


def search_queryset(queryset, search, fields, extra=None):
    for word in search.split()[:MAX_SEARCH_TERMS]:
        clause = Q()
        for field in fields:
            clause |= Q(**{f"{field}__icontains": word})
        if extra is not None:
            clause |= extra(word)
        queryset = queryset.filter(clause)
    return queryset


def paginate(request, queryset, *, search_fields=(), extra_search=None):
    search = parse_search(request.GET)
    page_size = parse_page_size(request.GET)
    if search:
        queryset = search_queryset(queryset, search, search_fields, extra_search)
    paginator = Paginator(queryset, page_size)
    page = paginator.get_page(parse_page_number(request.GET))
    return ListPage(page=page, search=search, page_size=page_size)


def _query_for(search, page_size, page_number=None):
    params = {}
    if search:
        params[SEARCH_PARAM] = search
    if page_size != DEFAULT_PAGE_SIZE:
        params[SIZE_PARAM] = page_size
    if page_number and page_number > 1:
        params[PAGE_PARAM] = page_number
    return urlencode(params)


def list_context(result):
    page = result.page
    paginator = page.paginator
    return {
        "page_obj": page,
        "paginator": paginator,
        "search": result.search,
        "page_size": result.page_size,
        "page_sizes": PAGE_SIZES,
        "page_links": list(
            paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1)
        ),
        "ellipsis": paginator.ELLIPSIS,
        "list_query": _query_for(result.search, result.page_size),
        "current_query": _query_for(result.search, result.page_size, page.number),
        "total_count": paginator.count,
        "first_index": page.start_index(),
        "last_index": page.end_index(),
    }


def preserved_query(request):
    params = {key: request.GET[key] for key in STATE_PARAMS if request.GET.get(key)}
    return urlencode(params)


def redirect_to_list(request, route_name):
    url = reverse(route_name)
    query = preserved_query(request)
    return redirect(f"{url}?{query}" if query else url)


class PaginatedSearchMixin:
    search_fields = ()

    def search_clause(self, word):
        return Q()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        result = paginate(
            self.request,
            self.get_queryset(),
            search_fields=self.search_fields,
            extra_search=self.search_clause,
        )
        context.update(list_context(result))
        context[self.get_context_object_name(self.object_list)] = result.page.object_list
        return context
