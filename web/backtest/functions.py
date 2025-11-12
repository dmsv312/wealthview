from django.db.models import Q
from backtest.models import *
from main.models import Country
from datetime import datetime


def asset_log(text='', file='error.log', mode='a'):
    dateTimeObj = datetime.now()
    date = dateTimeObj.strftime("%d-%b-%Y (%H:%M)")

    text = date + ": " + text + "\r\n"
    with open(file, mode) as the_file:
        the_file.write(text)


def asset_log_outdated_tickers(text={}, file='outdated.log', mode='a'):
    dateTimeObj = datetime.now()
    date = dateTimeObj.strftime("%d-%b-%Y (%H:%M)")
    with open(file, mode) as the_file:
        the_file.write(date)
        json.dump(text, the_file)
        the_file.write("\n")


def parse(ticker=None):
    # Репасринг по тикеру или всех тикеров
    from .tasks import parse_by_assets
    print("Starting reparsing")

    asset_type = Type.SIMPLE_ASSETS_TYPES
    assets = Asset.objects.filter(Q(split_update_date__lt=timezone.now()) | Q(split_update_date__isnull=True),
                                  type__in=asset_type,
                                  exchange__active=True,
                                  status__in=[0, 4])

    if ticker:
        ticker = ticker.upper()
        assets = assets.filter(exchange_ticker=ticker)

    if not assets:
        if ticker:
            print("No assets to parse for ticker {}".format(ticker))
        else:
            print("No assets to parse")
    else:
        assets.update(status=0)
        total = assets.count()
        # i = 0
        for each in assets:
            # i = i +1
            # asset_log("Parsing {}, {} of {}".format(each.exchange_ticker, i, total), "parse.log", "w")
            parse_by_assets.delay([each.id])


# each.reparse()


def remove_double_assets():
    for asset in Asset.objects.all():
        doubles = Asset.objects.filter(exchange=asset.exchange, exchange_ticker=asset.exchange_ticker)
        if doubles.count() >= 2:
            print(doubles.latest('id').delete())


def parse_assets(asset_types=["INDEX", "ETF", "Asset"]):
    # Парсинг новых ассетов

    from core.integrations.eod import EODService  # TODO вынести после успешных тестов в общий список импортов
    eod_service = EODService()

    EXCHANGE_GROUPS = ["MCX", "US", "INDX"]
    parsed_tickers = {}
    # US exchange group consist of all USA exchanges
    # INDX exchange group consist of all INDX exchanges
    for exchange_group in EXCHANGE_GROUPS:
        assets = eod_service.get_assets(exchange_group)
        assets_len = len(assets)
        print(assets_len)
        i = 0
        if assets:
            i += 1
            print(f'{i} / {assets_len}')
            for _asset in assets:
                code = _asset['Code'].upper()
                exchange_name = _asset['Exchange']

                exchange = Exchange.objects.filter(code__iexact=exchange_name).first()

                if not exchange:
                    if code == 'GBTC':
                        # создание биржи OTCQX при первом парсинге
                        exchange = Exchange.objects.create(code=exchange_name, name=exchange_name)
                    else:
                        print("no exchange found: %s" % exchange_name)
                        continue
                else:
                    # пропускать все активы с биржи OTCQX кроме GBTC
                    if exchange_name == 'OTCQX' and code != 'GBTC':
                        continue

                asset_type = _asset['Type']
                type_id = Type.VOCAB.get(asset_type)

                if type_id:
                    type = Type.objects.filter(slug=type_id).first()
                else:
                    print("no type found: %s" % asset_type)
                    continue

                try:
                    _Asset = Asset.objects.get(exchange_ticker__iexact=code, exchange=exchange)
                except Asset.DoesNotExist:
                    _Asset = Asset(exchange_ticker=code, exchange=exchange)

                _Asset.type = type

                _Asset.name = _asset['Name']
                country = _asset['Country']

                if country and country != "Unknown":
                    country = Country.objects.filter(name=country).first()
                    if country:
                        _Asset.country = country

                currency_id = _asset['Currency']

                currency = Currency.objects.filter(ticker=currency_id).first()

                if currency:
                    _Asset.currency = currency
                else:
                    print("no currency {} found. creating one...".format(currency_id))
                    _Asset.currency = Currency.objects.create(ticker=currency_id, name=currency_id)
                # continue

                if exchange_name in parsed_tickers:
                    if type_id in parsed_tickers[exchange_name]:
                        parsed_tickers[exchange_name][type_id].append(code)
                    else:
                        parsed_tickers[exchange_name].update({type_id: [code]})
                else:
                    parsed_tickers[exchange_name] = {type_id: [code]}

                print("Saving asset {}".format(_asset['Code']))

                if not _Asset.id:
                    _Asset.id = Asset.objects.latest('id').id + 1  # TODO без этой сран и integrityError
                _Asset.save()

    # change status to "outdated" to assets which changed exchange, type are already not showing in exchange assets list
    for exchange in Exchange.objects.all():
        exchange_code = exchange.code
        for ticker_type in Type.objects.filter(slug__in=["ET", "ST", "AC"]):
            # get current tickers
            all_tickers = set(list(
                Asset.objects.filter(exchange=exchange, type=ticker_type).exclude(status__in=[-1, 5]).values_list(
                    "exchange_ticker",
                    flat=True)))
            if parsed_tickers.get(exchange_code):
                if parsed_tickers[exchange_code].get(ticker_type.slug):
                    # get parsed tickers of this specific and exchange
                    # if we have tickers which haven't parsed - change it status
                    parsed_exchange_tickers = set(parsed_tickers[exchange_code][ticker_type.slug])
                    outdated_tickers = all_tickers - parsed_exchange_tickers
                    outdated_tickers_info = {ticker_type.slug: list(outdated_tickers)}
                    asset_log_outdated_tickers(text={exchange_code: outdated_tickers_info})
                    Asset.objects.filter(exchange_ticker__in=outdated_tickers, type=ticker_type,
                                         exchange=exchange).update(status=5)
                    print("outdated_tickers", {exchange_code: outdated_tickers_info})


def recalc(ticker=None):
    # Пересчет цен по тикеру или всех тикеров

    asset_type = Type.SIMPLE_ASSETS_TYPES
    assets = Asset.objects.filter(
        type__in=asset_type,
        exchange__active=True,
        status__in=[0, 4])

    if ticker:
        ticker = ticker.upper()
        assets = assets.filter(exchange_ticker=ticker)

    if not assets:
        if ticker:
            print("No assets to parse for ticker {}".format(ticker))
        else:
            print("No assets to parse")
    else:
        for each in assets:
            each.update_current_prices()
