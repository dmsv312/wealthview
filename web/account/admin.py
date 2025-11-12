from django.contrib import admin
from .models import *


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    pass


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = (
        'get_name', 'profile', 'benchmark', 'get_analysis_date',
        'get_ptf_yesterday', 'get_ptf_month', 'get_ptf_all', 'get_bench_yesterday', 'get_bench_month', 'get_bench_all')
    list_filter = ('profile', ("data", admin.EmptyFieldListFilter),)


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = ["pk", "type", "asset_type", "asset_name"]
    fields = ["date", "type", "count", "price", "cost", "portfolio"]
    list_filter = ['portfolio']

    def asset_type(self, obj):
        return obj.asset.type.title

    def asset_name(self, obj):
        return obj.asset.name


@admin.register(OperationType)
class OperationTypeAdmin(admin.ModelAdmin):
    pass
