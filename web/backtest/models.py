from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
import datetime
import requests
import json
from django.utils.dateparse import parse_date
# Create your models here.
# TODO: matching types and assets
from main.models import Country
from django.dispatch import receiver
from django_pandas.io import read_frame

from core.integrations.eod import EODService

"""
..............................................................................................................
................................................ COMMON MODELS ...............................................
..............................................................................................................
"""

"""
...................................................
...................... Currency  ..................
...................................................
"""


class Currency(models.Model):
    class Meta:
        verbose_name = "Валюта"
        verbose_name_plural = "Валюты"

    AVAILABLE_CURRENCIES = ["RUB", "USD"]
    ticker = models.CharField(max_length=3, primary_key=True, unique=True,
                              verbose_name="Тикер", help_text="Например: для 'Рубль' -> 'RUB'")
    name = models.CharField(max_length=32, unique=True, null=True,
                            verbose_name="Наименование валюты")

    # def save(self):
    #    self.ticker = self.ticker.upper()
    #    super(Currency, self).save()

    def __str__(self):
        return self.name


"""
...................................................
.................... Exchange  ....................
...................................................
"""


class Exchange(models.Model):
    class Meta:
        verbose_name = "Биржа"
        verbose_name_plural = "Биржи"

    code = models.CharField(max_length=32, primary_key=True, unique=True, verbose_name="Код биржи")
    active = models.BooleanField(default=True, verbose_name="Активная")
    name = models.CharField(max_length=64, unique=True, null=True, verbose_name="Название биржи")

    @property
    def real_code(self):
        # Вывод правильного кода US для парсинга американских бирж.
        code = self.code

        code_convert = [
            'NYSE ARCA',
            'NYSE',
            'NASDAQ',
            'BATS'
        ]

        if code in code_convert:
            code = 'US'

        return code

    def __str__(self):
        return "[{code}] {name}".format(
            code=self.code,
            name=self.name,
        )


"""
..............................................................................................................
................................................ ASSETS ......................................................
..............................................................................................................
"""
"""
...................................................
...................... Type model  ................
...................................................
"""


class Type(models.Model):
    # TODO: assettype
    class Meta:
        verbose_name = "Тип актива"
        verbose_name_plural = "Типы активов"

    SIMPLE_ASSETS_TYPES = ["ET", "ST", "FX"]
    BACKTEST_ASSETS_TYPES = ["ET", "ST", "CS"]
    BENCHMARKS_TYPES = ["ET", "AC"]
    VOCAB = {
        "Common Stock": "ST",
        "ETF": "ET",
        "INDEX": "AC"
    }
    slug = models.CharField(max_length=2, primary_key=True, unique=True,
                            verbose_name="Код в базе данных", help_text="Например: для 'Mutual Fond' -> 'MF'")
    title = models.CharField(max_length=32, unique=True, null=True,
                             verbose_name="Название типа")

    def save(self, *args, **kwargs):
        self.slug = self.slug.upper()
        super(Type, self).save(*args, **kwargs)

    def __str__(self):
        return self.title


"""
...................................................
...................... Asset model  ...............
...................................................
"""


class Asset(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['exchange_ticker']),
            models.Index(fields=['status']),
        ]
        verbose_name = "Актив"
        verbose_name_plural = "Активы"
        unique_together = ('exchange_ticker', 'exchange')

    ACTUAL_STATUSES = [4]

    # Common Stock
    type = models.ForeignKey(Type, verbose_name="Тип актива", on_delete=models.CASCADE)
    # ^DJI
    exchange_ticker = models.CharField(max_length=255, verbose_name="Тикер")
    # Dow Jones Industrial Average
    name = models.CharField(max_length=255, verbose_name="Полное название актива")
    # USA
    country = models.ForeignKey(Country, blank=True, null=True, on_delete=models.CASCADE,
                                verbose_name="Страна")
    # INDEX
    exchange = models.ForeignKey(Exchange, blank=True, null=True, on_delete=models.CASCADE,
                                 verbose_name="Биржа")
    # USD
    currency = models.ForeignKey(Currency, blank=True, null=True, on_delete=models.CASCADE,
                                 verbose_name="Валюта")

    split_update_date = models.DateField(null=True, blank=True, verbose_name='Дата обновления сплитов')
    price_update_date = models.DateField(null=True, blank=True, verbose_name='Дата обновления цен')
    fund_attributes_update_date = models.DateField(null=True, blank=True, verbose_name='Дата обновления аттрибутов')

    last_parse_splits = models.TextField(null=True, blank=True, editable=False)

    choices = (
        (-1, 'Ошибка'),
        (0, 'Ожидает парсинга'),
        (1, 'Парсинг сплитов'),
        (2, 'Парсинг цен'),
        (3, 'Обновление текущих цен'),
        (4, 'Актуален'),
        (5, 'Устарел'),
    )

    status = models.IntegerField(
        choices=choices,
        default=0, verbose_name="Статус"
    )

    @classmethod
    def get_default_benchmark(cls):
        return Asset.objects.get(exchange_ticker="IMOEX", exchange__code="INDX")

    @property
    def get_periods(self):
        prices = self.prices.all()

        df = read_frame(prices)

        return df

    @property
    def had_splits(self):
        # Есть ли сплиты
        return AssetsSplits.objects.filter(belongs_to=self).exists()

    @property
    def ticker_working_stocks(self):
        # Выводит список активных бирж
        assets = Asset.objects.filter(exchange_ticker=self.exchange_ticker, exchange__active=True).count()
        return assets

    @property
    def split_periods(self):
        # Выводит список периодов сплитов если таковые имеются
        periods = []
        all_splits = AssetsSplits.objects.filter(belongs_to=self).order_by("date")

        last_split = None
        for split in all_splits:

            if not last_split:
                date_from = parse_date('1900-01-01')
            else:
                date_from = last_split.date

            upper_splits = AssetsSplits.objects.filter(belongs_to=self, date__gt=split.date).order_by("-date")

            all_splits = [x.split for x in upper_splits]
            all_splits.append(split.split)

            periods.append({
                "date_from": date_from,
                "date_to": split.date,
                "splits": all_splits
            })

            last_split = split

        if not last_split:
            date_from = parse_date('1900-01-01')
        else:
            date_from = last_split.date

        periods.append({
            "date_from": date_from,
            "date_to": datetime.date.today(),
            "splits": []
        })

        return periods

    def reparse(self):
        # Полный репарсинг сплитов и цен
        # self.update_current_prices()
        self.update_splits()
        self.update_prices()
        self.update_attributes()

    def update_current_prices(self):
        # Обновление текущих цен на основании сплитов

        # if json.dumps(str(self.split_periods)) != self.last_parse_splits:
        print("Recalculating asset {}".format(self.name))
        prices = AssetsPrices.objects.filter(asset=self).all()

        if prices:
            self.status = 3
            self.save()
            for price in prices:
                price.recalc_price()
            self.status = 4
            self.save()

    def update_splits(self):
        # Парсинг сплитов
        each = self
        self.status = 1
        self.save()
        print("Updating splits for {}".format(self.name))
        from .functions import asset_log

        current_splits = AssetsSplits.objects.filter(belongs_to=each).count()

        asset = (each.exchange_ticker + '.' + each.exchange.real_code)
        date_from = '1900-01-01'
        date_to = timezone.now().strftime('%Y-%m-%d')
        if self.split_update_date:
            date_from = self.split_update_date.strftime('%Y-%m-%d')

        eod_service = EODService()

        answer = eod_service.get_splits(asset, date_from, date_to)

        try:
            for even in answer:
                if AssetsSplits.objects.filter(belongs_to=each).filter(date=even['date']):
                    continue
                else:
                    new_split = AssetsSplits.objects.create(belongs_to=each, date=even['date'], split=even['split'])
                    new_split.save()

            self.split_update_date = timezone.now()
            self.last_parse_splits = json.dumps(str(self.split_periods))
            self.status = 4
            self.save()

        except Exception as err:
            self.status = -1
            self.save()

    def update_attributes(self):

        eod_service = EODService()

        exchange_real_code = self.exchange.real_code

        # костыль для GBTC, получение в связке с биржей OTCQX не работает
        if self.exchange.real_code == 'OTCQX':
            exchange_real_code = 'US'

        json_response = eod_service.get_prices(self.exchange_ticker + '.' + exchange_real_code)
        self.status = 2
        self.save()

        data = json_response.get("General")

        if not data:
            self.status = 4
            self.save()
            return

        etf_data = json_response.get("ETF_Data", None)
        highlights = json_response.get("Highlights", None)
        splits_dividends = json_response.get("SplitsDividends", None)

        try:
            earnings_history = json_response['Earnings']['History']
        except KeyError:
            earnings_history = None

        dividend_yield = None
        ex_dividend_date = None
        dividend_share = None
        report_date = None
        market_capitalization = None
        sector = None
        industry = None

        if highlights:
            if highlights.get("DividendYield", None) is not None:
                dividend_yield = float(highlights.get("DividendYield")) * 100

            if highlights.get("DividendShare", None) is not None:
                dividend_share = float(highlights.get("DividendShare"))

            if highlights.get("MarketCapitalization", None) is not None:
                market_capitalization = float(
                    '{:.3f}'.format(float(highlights.get("MarketCapitalization")) / 1000000000))

        if splits_dividends:

            if splits_dividends.get("ExDividendDate", None) is not None:
                try:
                    ex_dividend_date = parse_date(splits_dividends.get("ExDividendDate"))
                except:
                    pass

        if earnings_history:

            earnings_history_report_dates = sorted([parse_date(d['reportDate']) for d in earnings_history.values()])

            for date in earnings_history_report_dates:
                if date >= datetime.datetime.now().date():
                    print(date)
                    report_date = date
                    break

        params = {
            "сode": data.get('Code', ""),
            "name": data.get('Name', ""),
            "country_name": data.get('CountryName', ""),
            "exchange": data.get('Exchange', ""),
            "currency_code": data.get('CurrencyCode', ""),
            "isin": data.get('ISIN', ""),
            "category": data.get('Category', ""),
            "dividend_yield": dividend_yield,
            "dividend_share": dividend_share,
            "ex_dividend_date": ex_dividend_date,
            "report_date": report_date,
            "market_capitalization": market_capitalization,
            "sector": data.get('Sector', ""),
            "industry": data.get('Industry', "")
        }

        if etf_data:
            params['company_name'] = etf_data.get('Company_Name', "")

            if len(params['isin']) == 0 and etf_data.get("ISIN", None):
                params['isin'] = etf_data.get("ISIN")

        params_object, created = AssetFundAttributes.objects.get_or_create(asset=self)
        AssetFundAttributes.objects.filter(pk=params_object.id).update(**params)

        self.fund_attributes_update_date = timezone.now()
        self.status = 4
        self.save()

    def update_prices(self):
        # Парсинг цен
        from dateutil.relativedelta import relativedelta
        each = self
        self.status = 2
        self.save()
        prices_request_url = 'https://eodhistoricaldata.com/api/eod/{asset}?from={date_from}&to={date_to}&api_token=3fa9o8ba134f90.20329410&period={period}&fmt=json'

        eod_service = EODService()
        # TODO eod_service.get_prices()

        print("Updating prices for {}".format(self.name))

        intervals = ['d']
        for interval in intervals:
            date_from = '1900-01-01'
            date_to = timezone.now().strftime('%Y-%m-%d')
            if self.price_update_date:
                delta = relativedelta(months=1)
                date_from = self.price_update_date - delta
                date_from = date_from.strftime('%Y-%m-%d')

            if each.exchange:
                url = prices_request_url.format(asset=(each.exchange_ticker + '.' + each.exchange.real_code),
                                                period=interval, date_from=date_from, date_to=date_to)
                print("Getting url " + url)
            else:
                self.status = -1
                self.save()
                print(each.pk)
                continue

            request = requests.get(url, timeout=None)
            try:
                answer = json.loads(request.text)
                if answer == []:
                    self.status = -1
                    self.price_update_date = timezone.now()
                    self.save()
            except Exception as err:
                asset_log("{}, error: {}, url: {}, answer: {}".format(self.exchange_ticker, err, url, request.text))
                print(err, '\n', request.text)
                self.status = -1
                self.price_update_date = timezone.now()
                self.save()
                continue

            self.price_update_date = timezone.now()
            self.status = 4
            self.save()
            print(self.status)
            continue
            if len(answer):

                for even in answer:
                    if not even['close']:
                        continue

                    if each.prices.filter(date=parse_date(even['date'])).exists():
                        # print('Asset {asset} already has Splits for date {date}'.format(asset=each.exchange_ticker, date=even['date']))
                        continue

                    if AssetsPrices.objects.filter(asset=each).filter(interval=interval).filter(date=even['date']):
                        pass
                    else:

                        price = even['close']

                        try:
                            new_price = each.prices.create(interval=interval,
                                                           price=even['close'],
                                                           date=even['date'],
                                                           price_after_split=price)
                            new_price.save()

                            new_price = AssetsPrices.objects.filter(pk=new_price.id).first()
                            new_price.recalc_price()
                        except Exception as err:
                            print('Error: ', err)
                            print("Param's:\n",
                                  'Ticker =', each.exchange_ticker,
                                  'Price =', even['close'],
                                  'Date =', even['date'],
                                  'Price_after_split', price)

        # self.price_update_date = timezone.now()
        # self.status = 4
        # self.save()

    def save(self, *args, **kwargs):
        self.exchange_ticker = self.exchange_ticker.upper()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.exchange.code}" if self.exchange else "" + "{name} {type} ({ticker})".format(
            name=self.name,
            type=self.type,
            ticker=self.exchange_ticker
        )

    @property
    def as_suggestion(self):
        exchange = "" if self.exchange is None else "{exchange}: ".format(exchange=self.exchange.code)
        return "{name} ({exchange}{ticker})".format(
            name=self.name,
            exchange=exchange,
            ticker=self.exchange_ticker
        )

    @staticmethod
    def get_available_benchmarks():
        exchange = Exchange.objects.get(code="INDX")
        tickers = ["IMOEX", "MCFTR", "SP500TR", "GSPC", "IXIC", "NDX", "ACWI", "MSCIWORLD"]
        benchmarks = Asset.objects.filter(exchange_ticker__in=tickers, exchange=exchange)

        available_benchmarks = []
        for ticker in tickers:
            for benchmark in benchmarks:
                if ticker == benchmark.exchange_ticker:
                    available_benchmarks.append(benchmark)
                    break

        return available_benchmarks


"""
Asset attributes
"""


class AssetFundAttributes(models.Model):
    asset = models.OneToOneField(Asset,
                                 on_delete=models.CASCADE,
                                 related_name='fund_attributes',
                                 # editable=False,
                                 verbose_name="Фунд. аттрибуты")

    сode = models.CharField(max_length=255, verbose_name="Тикер", blank=True, null=True)
    name = models.CharField(max_length=255, verbose_name="Имя", blank=True, null=True)
    country_name = models.CharField(max_length=255, verbose_name="Рынок", blank=True, null=True)
    exchange = models.CharField(max_length=255, verbose_name="Биржа", blank=True, null=True)
    currency_code = models.CharField(max_length=255, verbose_name="Валюта торгов", blank=True, null=True)
    isin = models.CharField(max_length=255, verbose_name="ISIN", blank=True, null=True)
    company_name = models.CharField(max_length=255, verbose_name="Эмитент", blank=True, null=True)
    category = models.CharField(max_length=255, verbose_name="Объект инвестирования", blank=True, null=True)

    dividend_yield = models.FloatField(verbose_name="Дивидендная доходность", blank=True, null=True)
    dividend_share = models.FloatField(verbose_name="Размер дивиденда", blank=True, null=True)
    ex_dividend_date = models.DateField(verbose_name="Дата див. отсечки", blank=True, null=True)
    report_date = models.DateField(verbose_name="Дата отчетности", blank=True, null=True)
    market_capitalization = models.FloatField(verbose_name="Рыночная капитализация", blank=True, null=True)
    sector = models.CharField(max_length=255, verbose_name="Сектор", blank=True, null=True)
    industry = models.CharField(max_length=255, verbose_name="Отрасль", blank=True, null=True)

    def __str__(self):
        return '{owner}'.format(id=self.id, owner=self.asset)


"""
...................................................
...................... Assets prices  ..............
...................................................
"""


class AssetsPrices(models.Model):
    PERIODS = (
        ('d', 'Day'),
        ('w', 'Week'),
        ('m', 'Month'),
    )

    asset = models.ForeignKey(Asset,
                              limit_choices_to={"type_id__in": Type.SIMPLE_ASSETS_TYPES},
                              on_delete=models.CASCADE,
                              related_name='prices',
                              # editable=False,
                              verbose_name="Актив")
    interval = models.CharField(max_length=5, choices=PERIODS, verbose_name='Интервалы')
    price = models.FloatField(verbose_name='Цена актива')
    date = models.DateField(verbose_name='Дата')
    price_after_split = models.FloatField(verbose_name='Цена после дробления')

    def __str__(self):
        return '[Split #{id}]: {owner}'.format(id=self.id, owner=self.asset)

    def recalc_price(self):
        # Пересчет цен

        price = self.price
        for date in self.asset.split_periods:
            try:

                if date['date_from'] <= self.date <= date['date_to']:

                    for split_element in date['splits']:
                        split = split_element.split('/')

                        if date['date_to'] != self.date:
                            price *= float(split[1])
                            price /= float(split[0])

            except Exception as err:
                print(err)
                continue
        try:
            self.price_after_split = price
            self.save()

        except Exception as err:
            print('Error: ', err)
            print("Param's:\n",
                  'Ticker =', self.asset.exchange_ticker,
                  'Price =', self.price,
                  'Date =', self.date,
                  'Price_after_split', price)

    class Meta:

        indexes = [
            models.Index(fields=['asset']),
        ]
        ordering = ['-date']
        verbose_name = 'Цена на актив'
        verbose_name_plural = 'Цены на активы'


"""
...................................................
...................... Assets splits  ..............
...................................................
"""


class AssetsSplits(models.Model):
    belongs_to = models.ForeignKey(Asset,
                                   limit_choices_to={"type_id__in": Type.SIMPLE_ASSETS_TYPES},
                                   # related_name='splits',
                                   on_delete=models.CASCADE,
                                   # editable=False,
                                   verbose_name='Актив')
    date = models.DateField(verbose_name='Дата дробления')
    split = models.CharField(max_length=32, verbose_name='Коэффициент дробления')

    @property
    def real_date(self):
        from datetime import datetime, timedelta
        return self.date - timedelta(days=1)

    class Meta:
        indexes = [
            models.Index(fields=['belongs_to']),
        ]
        verbose_name = 'Дробление актива'
        verbose_name_plural = 'Дробления активов'

    def __str__(self):
        return '[Split #{id}]: {owner}'.format(id=self.id, owner=self.belongs_to)


@receiver(models.signals.post_save, sender=AssetsSplits)
def after_save_split(sender, instance, created=False, **kwargs):
    if created:
        # Пересчет цен после добавление сплита
        # recalc_prices_after_split_change.delay(instance.belongs_to.id)

        prices = instance.belongs_to.prices.all()

        if prices:
            print("Updating old prices for {}".format(instance.belongs_to.name))
            instance.belongs_to.status = 3
            instance.belongs_to.save()
            for price in prices:
                price.recalc_price()
            instance.belongs_to.status = 4
            instance.belongs_to.save()


# @receiver(models.signals.post_delete, sender=AssetsSplits)
# def after_save_split(sender, instance, created=False, **kwargs):

#     if instance.belongs_to.status not in [1,3]:
#         prices = instance.belongs_to.assetsprices_set.all()

#         if prices:
#             arr = []

#             for price in prices:
#                 arr.append(price.id)

#             recalc_prices_after_split_change.delay(arr, instance.belongs_to.id)

"""
..............................................................................................................
................................................ INVESTMENTS .................................................
..............................................................................................................
"""
"""
...................................................
...................... Portfolio  .................
...................................................
"""

# TODO: min length?
# TODO: can't create without investments?
# class Portfolio(models.Model):
#     class Meta:
#         indexes = [
#             models.Index(fields=['owner']),
#             models.Index(fields=['currency']),
#             models.Index(fields=['benchmark']),
#         ]
#         verbose_name = "Портфель"
#         verbose_name_plural = "Портфели"
#
#     owner = models.ForeignKey(User, related_name="portfolios", on_delete=models.CASCADE,
#                               verbose_name="Владелец портфеля")
#     start_date = models.DateField(verbose_name="Начальная дата")
#     end_date = models.DateField(verbose_name="Конечная дата")
#     investment_sum = models.FloatField(verbose_name="Сумма инвестиций")
#     currency = models.ForeignKey(Currency,
#                                  limit_choices_to={"ticker__in": Currency.AVAILABLE_CURRENCIES},
#                                  on_delete=models.CASCADE,
#                                  verbose_name="Валюта инвестиций",)
#     benchmark = models.ForeignKey(Asset,
#                                   limit_choices_to={"type_id__in": Type.BENCHMARKS_TYPES},
#                                   on_delete=models.CASCADE,
#                                   default=21891,    # Moscow Exchange
#                                   verbose_name="Бенчмарк")
#
#     def __str__(self):
#         return "[Portfolio #{id}]: {owner}, {sum} {currency}, {benchmark}".format(
#             id=self.id,
#             owner=self.owner,
#             sum=self.investment_sum,
#             currency=self.currency.ticker,
#             benchmark=self.benchmark.exchange_ticker,
#         )


"""
...................................................
...................... Investment  ................
...................................................
"""

# class Investment(models.Model):
#     # TODO: Validate share
#     class Meta:
#         indexes = [
#             models.Index(fields=['portfolio']),
#             models.Index(fields=['asset']),
#         ]
#         verbose_name = "Инвестиция"
#         verbose_name_plural = "Инвестиции"
#
#     portfolio = models.ForeignKey(Portfolio, verbose_name="Портфель инвестиции", related_name="investments",
#                                   on_delete=models.CASCADE)
#     asset = models.ForeignKey(Asset,
#                               limit_choices_to={"type_id__in": Type.SIMPLE_ASSETS_TYPES},
#                               on_delete=models.CASCADE,
#                               verbose_name="Актив")
#     share = models.FloatField(verbose_name="Доля актива портфеле")
#
#     def __str__(self):
#         return "[{share}%] {asset}".format(
#             share=self.share,
#             asset=self.asset,
#         )

# def get_assets(self):
#     pass


"""
..............................................................................................................
................................................ OTHER .......................................................
..............................................................................................................
"""


class DatesOfPricesUpdates(models.Model):
    STATUSES = (
        ('s', 'Started'),
        ('f', 'Completed')
    )
    date = models.DateTimeField(max_length=50, auto_now_add=True, db_index=True, verbose_name='Дата добавления')
    status = models.CharField(max_length=60, choices=STATUSES, default='s', verbose_name='Статус обновления')

    class Meta:
        verbose_name = 'Дата обновления'
        verbose_name_plural = 'Даты обновления'
