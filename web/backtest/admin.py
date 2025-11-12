from django.contrib import admin
from django.conf.urls import url
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from backtest.tasks import parse_by_assets, reparse_all, recalc_prices_after_split_change, recalc_all, reparse_attribs, \
    parse_assets, reparse_all_attribs, update_bot_profile
from .models import Type, Asset, AssetsPrices, AssetsSplits, Currency, Exchange, DatesOfPricesUpdates, \
    AssetFundAttributes
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.db import connection
from django.utils.functional import cached_property
import logging

# Register your models here.
"""
..............................................................................................................
................................................ COMMON ......................................................
..............................................................................................................
"""

logger = logging.getLogger(__name__)


class LargeTablePaginator(Paginator):
    @cached_property
    def count(self):
        query = self.object_list.query
        if not query.where:
            try:
                cursor = connection.cursor()
                cursor.execute('SELECT reltuples FROM pg_class WHERE relname = %s', [query.model._meta.db_table])
                return int(cursor.fetchone()[0])
            except Exception as e:  # noqa
                logger.warning(e)

        return super().count


class CurrencyAdmin(admin.ModelAdmin):
    list_display = ["ticker", "name"]


def make_active(modeladmin, request, queryset):
    objects = queryset.all()
    for item in objects:
        item.active = True
        item.save()


make_active.short_description = "Сделать активной"


def make_deactive(modeladmin, request, queryset):
    objects = queryset.all()
    for item in objects:
        item.active = False
        item.save()


make_deactive.short_description = "Сделать не активной"


class ExchangeAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "active"]
    list_filter = ["active"]
    actions = [make_active, make_deactive]


"""
..............................................................................................................
................................................ ASSETS ......................................................
..............................................................................................................
"""


class TypeAdmin(admin.ModelAdmin):
    list_display = ["slug", "title"]


class IsHadSplits(admin.SimpleListFilter):
    title = 'Сплиты'
    parameter_name = 'had_splits'

    def lookups(self, request, model_admin):
        return (
            ('Yes', 'Да'),
            ('No', 'Нет'),
        )

    def queryset(self, request, queryset):

        value = self.value()
        # return queryset.filter(assetssplits__isnull=False).distinct()
        if value == 'Yes':
            return queryset.filter(assetssplits__isnull=False).distinct()
        elif value == 'No':
            return queryset.filter(assetssplits__isnull=True).distinct()
        return queryset


class IsActiveExchange(admin.SimpleListFilter):
    title = 'Активные биржи'
    parameter_name = 'is_active'

    def lookups(self, request, model_admin):
        return (
            ('Yes', 'Да'),
            ('No', 'Нет'),
        )

    def queryset(self, request, queryset):

        value = self.value()
        # return queryset.filter(assetssplits__isnull=False).distinct()
        if value == 'Yes':
            return queryset.filter(exchange__active=True)
        elif value == 'No':
            return queryset.filter(exchange__active=False)
        return queryset


class IsParsed(admin.SimpleListFilter):
    title = 'Ранее спарсенные'
    parameter_name = 'is_parsed'

    def lookups(self, request, model_admin):
        return (
            ('Yes', 'Да'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        # return queryset.filter(assetssplits__isnull=False).distinct()
        if value == 'Yes':
            return queryset.exclude(price_update_date=None)

        return queryset


def recalc(modeladmin, request, queryset):
    objects = queryset.all()
    ids = []
    for item in objects:
        ids.append(str(item.id))

    recalc_prices_after_split_change.delay(",".join(ids))


recalc.short_description = "Пересчитать текущие цены"


def get_attribs(modeladmin, request, queryset):
    objects = queryset.all()
    ids = []
    for item in objects:
        ids.append(item.id)

    reparse_attribs.delay(ids)


get_attribs.short_description = "Обновить аттрибуты"


def reparse(modeladmin, request, queryset):
    objects = queryset.all()
    ids = []
    for item in objects:
        ids.append(item.id)

    parse_by_assets.delay(ids, True)


reparse.short_description = "Обновить сплиты и цены"


class AssetAttributesInline(admin.StackedInline):
    model = AssetFundAttributes


class AssetAdmin(admin.ModelAdmin):
    list_display = ["exchange_ticker", "name", "country", "exchange", "currency", "type", "id", "price_update_date",
                    "had_splits", "status", "ticker_working_stocks"]
    search_fields = (
        'exchange_ticker',
        'name'
    )
    list_filter = ['exchange', 'country', IsHadSplits, IsActiveExchange, IsParsed, "status", "type"]

    inlines = [AssetAttributesInline]

    def had_splits(self, obj):
        return "Да" if obj.had_splits else "Нет"

    had_splits.short_description = 'Сплиты'

    def ticker_working_stocks(self, obj):
        return obj.ticker_working_stocks

    ticker_working_stocks.short_description = 'Кол-во акт. бирж'

    def get_urls(self):
        urls = super().get_urls()

        new_urls = [
            # url(r'^update_assets_prices/$', self.admin_site.admin_view(self.update_assets_prices), name='Спарсить новые данные'),
            # url(r'^recalc_assets_prices/$', self.admin_site.admin_view(self.recalc_assets_prices), name='Пересчитать все цены'),
            url(r'^update_portfolios/$', self.admin_site.admin_view(self.update_portfolios)),
            url(r'^reparse_assets/$', self.admin_site.admin_view(self.reparse_assets)),
            url(r'^reparse_all_attribs/$', self.admin_site.admin_view(self.reparse_all_attribs), name='Обновить атрибуты'),

        ]
        return new_urls + urls

    def update_assets_prices(self, request):
        reparse_all.delay()
        return HttpResponseRedirect('/admin/backtest/asset/')

    def update_portfolios(self, request):
        from account.models import Portfolio
        for p in Portfolio.objects.all():
            update_bot_profile.delay(p.id)
        return HttpResponseRedirect('/admin/backtest/asset/')

    def reparse_assets(self, request):
        parse_assets.delay()
        return HttpResponseRedirect('/admin/backtest/asset/')

    def recalc_assets_prices(self, request):
        recalc_all.delay()
        return HttpResponseRedirect('/admin/backtest/asset/')

    def reparse_all_attribs(self, request):
        reparse_all_attribs.delay()
        return HttpResponseRedirect('/admin/backtest/asset/')

    actions = [recalc, reparse, get_attribs]
    # list_select_related = (
    #     'exchange_ticker',
    # )
    # search_fields = ('country',)
    # prepopulated_fields = {'name': ('exchange_ticker', )}


class AssetsPricesAdmin(admin.ModelAdmin):
    list_display = ['id', 'asset', 'interval', 'price', 'date', 'price_after_split']
    search_fields = [
        # 'asset__name',
        '=asset__exchange_ticker',
        # 'interval',
        'date'
    ]
    list_filter = ['interval', 'asset__exchange']
    readonly_fields = ['asset']
    list_select_related = (
        'asset',
        'asset__exchange'
    )

    paginator = LargeTablePaginator

    def change_list(self, request):
        context = dict(self.admin_site.each_context(request))
        return TemplateResponse(request, 'admin/backtest/change_list.html', context)


class AssetsAttributesAdmin(admin.ModelAdmin):
    readonly_fields = ['asset']


class AssetsSplitsAdmin(admin.ModelAdmin):
    list_display = ['id', 'belongs_to', 'date', 'split']
    search_fields = ['belongs_to__name', 'belongs_to__exchange_ticker', 'date', 'split']

    # readonly_fields = ['belongs_to']

    def real_date(self, obj):
        return obj.real_date

    real_date.short_description = 'Реальная дата дробления'

    def get_readonly_fields(self, request, obj=None):
        if obj:  # This is the case when obj is already created i.e. it an edit
            return ['belongs_to']
        else:
            return []

    # def get_form(self, request, obj=None, **kwargs):
    #     orig_self_form = self.form
    #     if not obj:
    #         self.form = CreateEntityForm
    #     result = super().get_form(request, obj=obj, **kwargs)
    #     self.form = orig_self_form
    #     return result


"""
..............................................................................................................
................................................ INVESTMENTS .................................................
..............................................................................................................
"""

# class InvestmentAdmin(admin.ModelAdmin):
#     # TODO: owner ?
#     list_display = ["portfolio", "asset", "share"]
#
#
# class PortfolioAdmin(admin.ModelAdmin):
#     list_display = ["id", "owner", "start_date", "end_date", "investment_sum", "currency", "benchmark"]


"""
..............................................................................................................
................................................ OTHER .................................................
..............................................................................................................
"""


class DatesOfPricesUpdatesAdmin(admin.ModelAdmin):
    list_display = ['date', 'status']


# common
admin.site.register(Currency, CurrencyAdmin)
admin.site.register(Exchange, ExchangeAdmin)
# assets
admin.site.register(Type, TypeAdmin)
admin.site.register(Asset, AssetAdmin)
admin.site.register(AssetsPrices, AssetsPricesAdmin)
admin.site.register(AssetsSplits, AssetsSplitsAdmin)
# investments
# admin.site.register(Investment, InvestmentAdmin)
# admin.site.register(Portfolio, PortfolioAdmin)
# other
admin.site.register(DatesOfPricesUpdates, DatesOfPricesUpdatesAdmin)

admin.site.register(AssetFundAttributes, AssetsAttributesAdmin)
