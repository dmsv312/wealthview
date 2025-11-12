import time

from django.utils import timezone

from django.db.models import Q
from sentry_sdk import capture_exception

from WealthView.celery import app


@app.task
def update_bot_profile(portfolio_id):
    from account.models import Portfolio
    from account.views import AnalyzeMixin
    from account.cache import PortfolioCache

    portfolio = Portfolio.objects.get(id=portfolio_id)

    mixin = AnalyzeMixin()
    mixin.ptf_cache = PortfolioCache(portfolio)

    analysis_data = mixin.analyze(session=None, portfolio=portfolio, update_cache=True)

    try:
        assert analysis_data.get('analysis_errors') is None
    except AssertionError as e:
        capture_exception(e)


@app.task
def update_bot_profiles():
    from account.models import Profile

    for profile in Profile.objects.exclude(tg_chat_id=''):
        for portfolio in profile.profile_portfolios.all():
            update_bot_profile.delay(portfolio.id)


@app.task
def parse_by_assets(assets, forced=False):
    # Парсинг по массивам id ассетов
    i = 0
    from backtest.models import Asset, AssetsPrices
    from backtest.functions import asset_log
    for asset in assets:
        i = i + 1
        if not forced:
            asset = Asset.objects.filter(pk=asset, status__in=[0, 4]).first()
        else:
            asset = Asset.objects.filter(pk=asset).first()
        asset_log("Parsing {}, {} of {}".format(asset.exchange_ticker, i, len(assets)), "parse.log", "a")

        if asset:
            time.sleep(1)
            asset.reparse()


@app.task
def reparse_attribs(assets):
    # Парсинг по массивам id ассетов
    from backtest.models import Asset, AssetsPrices
    for asset in assets:
        asset = Asset.objects.filter(pk=asset, status__in=[0, 4]).first()

        if asset:
            asset.update_attributes()


@app.task
def reparse_all_attribs():
    # Обновление атрибутов у всех активов
    from backtest.models import Type, Asset
    assets = Asset.objects.filter(status__in=Asset.ACTUAL_STATUSES)
    for asset in assets:
        asset.update_attributes()


@app.task
def update_attribs():
    from backtest.models import Asset
    for asset in Asset.objects.filter(status=0):
        reparse_attribs.delay([asset.id])


@app.task
def reparse_users_attribs():
    # Обновление атрибутов у всех активов
    from backtest.models import Asset
    from account.models import Operation

    user_assets = Operation.objects.values_list('asset', flat=True).distinct()
    assets = Asset.objects.filter(id__in=user_assets, status__in=Asset.ACTUAL_STATUSES)
    for asset in assets:
        reparse_attribs([asset.id])


@app.task
def recalc_prices_after_split_change(assets_id):
    # Пересчет цен после изменения сплита
    from backtest.models import Asset, AssetsPrices

    assets = assets_id.split(",")

    for asset in assets:
        asset = int(asset)
        asset = Asset.objects.filter(pk=asset).first()

        prices = AssetsPrices.objects.filter(asset=asset).all()

        if prices:
            asset.status = 3
            asset.save()

            for price in prices:
                price.recalc_price()

            asset.status = 4
            asset.save()


@app.task
def reparse_all():
    # Полный репарсинг
    # from backtest.functions import parse
    # parse()
    from backtest.models import Type, Asset

    print("Starting reparsing")

    asset_type = Type.SIMPLE_ASSETS_TYPES
    assets = Asset.objects.filter(Q(split_update_date__lt=timezone.now()) | Q(split_update_date__isnull=True),
                                  type__in=asset_type,
                                  exchange__active=True,
                                  status__in=[0, 4])

    if not assets:
        print("No assets to parse")
    else:
        assets.update(status=0)
        total = assets.count()
        # i = 0
        for each in assets:
            # i = i +1
            # asset_log("Parsing {}, {} of {}".format(each.exchange_ticker, i, total), "parse.log", "w")
            parse_by_assets.delay([each.id])


@app.task
def parse_assets():
    # Полный репарсинг
    from backtest.functions import parse_assets
    parse_assets()


@app.task
def recalc_all():
    # Полный перерасчет цен
    from backtest.functions import recalc
    recalc()
