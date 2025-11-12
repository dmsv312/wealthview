# Create your views here.
from typing import Type

from django.db.models import Count
from django_filters import FilterSet

from query_tools.filters import DateFilter

"""
..............................................................................................................
................................................ FILTER  .....................................................
..............................................................................................................
"""


def get_filtered_qs(request, queryset, model_filter: Type[FilterSet]):
    # Filter qs by pub state
    queryset = filter_by_pub_state(request, queryset)
    # Filter qs by date_range
    queryset = filter_by_date_range(request, queryset)
    # Filter qs by model_filter
    filtered_qs = model_filter(request.GET, queryset=queryset).qs
    return filtered_qs


def filter_by_pub_state(request, queryset):
    if queryset:
        if getattr(queryset[0], "pub_state", False):
            return queryset.filter(pub_state="PB")
    return queryset


def filter_by_date_range(request, queryset):
    # Get date_range
    date_range = request.GET.get("date_range")
    date_range = "all" if date_range is None else date_range
    # Get filter
    range_filter = DateFilter.get_range_filter(date_range)
    # Filter by range
    return range_filter(queryset)


"""
..............................................................................................................
................................................ SORT ........................................................
..............................................................................................................
"""


def get_sorted_qs(request, queryset):
    # Get order_by
    order_by = request.GET.get("order_by")
    order_by = "-date" if order_by is None else order_by
    # Annotate qs
    if order_by.__contains__("rating"):
        queryset = queryset.annotate(rating=Count('likes', distinct=True) - Count('dislikes', distinct=True))
    elif order_by.__contains__("popularity"):
        queryset = queryset.annotate(popularity=Count('comments', distinct=True))
    # ORDER BY qs
    queryset = queryset.order_by(order_by)
    return queryset
