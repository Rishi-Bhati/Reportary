"""
Shared pagination.

There was no pagination anywhere in the application: every list view rendered
its complete queryset, so page weight and query cost grew without bound with the
size of a project.
"""
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

DEFAULT_PER_PAGE = 25


def paginate(request, queryset, per_page=DEFAULT_PER_PAGE, param='page'):
    """
    Return a Page for `queryset`.

    A Page is iterable, so templates that loop over the old queryset keep
    working unchanged. Bad or out-of-range page numbers clamp to a valid page
    rather than raising.
    """
    paginator = Paginator(queryset, per_page)
    number = request.GET.get(param)
    try:
        return paginator.page(number)
    except PageNotAnInteger:
        return paginator.page(1)
    except EmptyPage:
        return paginator.page(paginator.num_pages)


def pagination_context(request, page, param='page'):
    """
    Context for the shared pagination control.

    `querystring` carries every current filter except the page number, so
    paging preserves the user's filters and sort order.
    """
    params = request.GET.copy()
    params.pop(param, None)
    querystring = params.urlencode()
    return {
        'page_obj': page,
        'paginator': page.paginator,
        'is_paginated': page.paginator.num_pages > 1,
        'pagination_querystring': f'{querystring}&' if querystring else '',
    }
