# -*- coding: utf-8 -*-
from django import forms

from backtest.models import Asset
from .models import Operation, OperationType, Portfolio


class OperationAddForm(forms.ModelForm):
    operation_type = forms.ModelChoiceField(to_field_name="slug", queryset=OperationType.objects.all())
    asset = forms.IntegerField()
    date = forms.DateField(input_formats=["%d-%m-%Y"])

    def __init__(self, *args, **kwargs):
        self.portfolio = kwargs.pop('portfolio')
        super(OperationAddForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Operation
        fields = ("count", "price", "cost", "portfolio")

    def clean(self):
        cleaned_data = super().clean()
        asset = cleaned_data.get("asset")
        print("asset", asset)
        if asset:
            asset_queryset = Asset.objects.filter(pk=asset, status__in=Asset.ACTUAL_STATUSES)
            if asset_queryset.exists():
                cleaned_data["asset_pk"] = asset
                asset = asset_queryset.first()
                cleaned_data["asset"] = asset
                cleaned_data["asset_type"] = asset.type
                if asset.type.slug != "CS" and self.portfolio.portfolio_operations.all().count() == 0:
                    self.errors.update({"analysis_errors": "Недостаточно средств"})

        else:
            self.errors.update({"analysis_errors": "Такого актива не существует"})


class PortfolioChangeSettingsForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ("benchmark", "currency")
