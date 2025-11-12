from datetime import date, timedelta
from typing import Type

from django_filters import FilterSet
from django.db import models

from reviews.models import *


class DateFilter(object):

    class Meta:
        today = date.today()

    @classmethod
    def get_range_filter(cls, date_range):
        if date_range == "today":
            return cls.filter_today
        elif date_range == "week":
            return cls.filter_week
        elif date_range == "month":
            return cls.filter_month
        elif date_range == "all":
            return cls.filter_all
        else:
            return None

    @classmethod
    def filter_today(cls, queryset):
        return queryset.filter(date__day=cls.Meta.today.day,
                               date__month=cls.Meta.today.month,
                               date__year=cls.Meta.today.year)

    @classmethod
    def filter_week(cls, queryset):
        one_week_ago = cls.Meta.today - timedelta(days=7)
        return queryset.filter(date__gte=one_week_ago)

    @classmethod
    def filter_month(cls, queryset):
        one_month_ago = cls.Meta.today - timedelta(days=30)
        return queryset.filter(date__gte=one_month_ago)

    @classmethod
    def filter_all(cls, queryset):
        return queryset