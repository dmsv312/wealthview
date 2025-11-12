# -*- coding: utf-8 -*-
import binascii
import os

from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.conf import settings

from backtest.models import Asset, Currency


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    tg_token = models.CharField(max_length=16, blank=True)
    tg_chat_id = models.CharField(max_length=250, blank=True)

    send_notify_dividends = models.BooleanField(default=False)
    send_notify_dividends_at = models.DateTimeField(null=True, blank=True, db_index=True)
    send_notify_report_date = models.BooleanField(default=False)
    send_notify_report_date_at = models.DateTimeField(null=True, blank=True, db_index=True)

    send_daily_notify_dividends = models.BooleanField(default=False)
    send_daily_notify_dividends_at = models.DateTimeField(null=True, blank=True)
    send_daily_notify_report_date = models.BooleanField(default=False)
    send_daily_notify_report_date_at = models.DateTimeField(null=True, blank=True)

    actual_r_test = models.ForeignKey('rprofile.RTestResult', null=True, blank=True, related_name='actual_r_test_results', on_delete=models.SET_NULL)

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

    def __str__(self):
        return self.user.email or self.user.username or f'Пользователь #{self.user.id}'

    def get_bot_link(self):
        return f'https://t.me/{settings.BOT_USERNAME}?start={self.tg_token}'

    def save(self, *args, **kwargs):
        if not self.tg_token:
            self.tg_token = binascii.hexlify(os.urandom(8)).decode()
        return super().save(*args, **kwargs)


class Portfolio(models.Model):
    PORTFOLIO_CURRENCIES = ("RUB", "USD")
    MIN_PORTFOLIOS_COUNT = 1
    MAX_PORTFOLIOS_COUNT = 3

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="profile_portfolios")
    benchmark = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True)
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True)
    data = models.JSONField(null=True, blank=True)
    name = models.CharField(default="", max_length=300, help_text="Имя портфолио")

    class Meta:
        verbose_name = "Портфель"
        verbose_name_plural = "Портфели"
        ordering = ("id", )

    def __str__(self):
        return f'{self.name} - {self.profile.user}'

    def get_name(self):
        return self.name or f'Портфель без названия ({self.id})'  # TODO нумерация портфелей

    def get_absolute_url(self):
        return reverse("account-page-portfolios-detail", args=[self.id])

    @staticmethod
    def get_default_settings():
        currency = Currency.objects.get(ticker="USD")
        benchmark = Asset.objects.all().first()
        name = "Портфель 1"
        return {"currency": currency, "benchmark": benchmark, "name": name}

    def get_analysis_date(self):
        try:
            return self.data.get('analysis_date')
        except Exception as e:
            return None

    def get_base_abs_profit(self, type_, period):
        from backtest.templatetags.backtest import smart_round
        try:
            return str(smart_round(self.data['portfolio_analysis_data']['abs_profit_by_periods'][type_][period])) + '%'
        except (KeyError, TypeError):
            return None

    def get_ptf_yesterday(self):
        return self.get_base_abs_profit('ptf', 'yesterday')

    def get_ptf_month(self):
        return self.get_base_abs_profit('ptf', 'one_month')

    def get_ptf_all(self):
        return self.get_base_abs_profit('ptf', 'all')

    def get_bench_yesterday(self):
        return self.get_base_abs_profit('bench', 'yesterday')

    def get_bench_month(self):
        return self.get_base_abs_profit('bench', 'one_month')

    def get_bench_all(self):
        return self.get_base_abs_profit('bench', 'all')


class OperationType(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    order = models.IntegerField(verbose_name='Порядок в выавдающем списке', default=0)

    class Meta:
        verbose_name = "Тип операции"
        verbose_name_plural = "Типы операций"
        ordering = ("order", )

    def __str__(self):
        return self.name


class Operation(models.Model):
    date = models.DateField(verbose_name="Дата транзакции")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, verbose_name="Актив")
    type = models.ForeignKey(OperationType, on_delete=models.CASCADE)
    count = models.FloatField(verbose_name="Количество", null=True, blank=True)
    price = models.FloatField(verbose_name="Цена", null=True, blank=True)
    cost = models.FloatField(verbose_name="Общая стоимость")
    portfolio = models.ForeignKey(Portfolio, related_name="portfolio_operations", on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Операция"
        verbose_name_plural = "Операции"
        ordering = ["-date", "-pk"]

    def __str__(self):
        return str(self.pk)
