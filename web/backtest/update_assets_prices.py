import requests
import json
from backtest.models import Asset, Type, AssetsPrices, AssetsSplits, DatesOfPricesUpdates
from django.utils import timezone
from django.db.models import Q
from django.conf import settings

split_request_url = 'https://eodhistoricaldata.com/api/splits/{asset}?api_token=3fa9o8ba134f90.20329410&from=1900-01-01&fmt=json'

prices_request_url = 'https://eodhistoricaldata.com/api/eod/{asset}?from=1900-01-01&to=2019-07-09&api_token=3fa9o8ba134f90.20329410&period={period}&fmt=json'

asset_type = Type.SIMPLE_ASSETS_TYPES

def new_splits_update():
    ticker = 'UPRO'
    assets = Asset.objects.filter(Q(split_update_date__lt=timezone.now()) | Q(split_update_date__isnull=True), 
        #type__in=asset_type, 
        exchange_ticker=ticker, 
        exchange__active=True)

    if not assets:
        print("No assets to check splits for ticker {}".format(ticker))

    for each in assets:
        each.update_splits()

def new_prices_update():
    ticker = 'UPRO'
    assets = Asset.objects.filter(Q(price_update_date__lt=timezone.now()) | Q(price_update_date__isnull=True), 
        #type__in=asset_type, 
        exchange_ticker=ticker, 
        exchange__active=True)

    if not assets:
        print("No assets to check prices for ticker {}".format(ticker))

    for each in assets:
        each.update_prices()


def splits_update():
    latest = DatesOfPricesUpdates.objects.order_by('-date')
    if not latest:
        start = DatesOfPricesUpdates()
        start.save()
        for each in Asset.objects.filter(type__in=asset_type, exchange_ticker='AAPL', exchange__active=True)[:10]:

            # stock_exchanges = {'USA': ['US',], 'Russia': ['US', 'MCX'], 'Germany': ['INDX',]}
            # if each.country is None:
            #     continue
            # for stock_exchange in stock_exchanges[each.country.name]:
            #     request = requests.get(split_request_url.format(asset=(each.exchange_ticker + '.' + stock_exchange)))
            #     try:
            #         answer = json.loads(request.text)
            #     except Exception as err:
            #         print(err, '\n', request.text)
            #         continue
            #     if len(answer):
            #         for even in answer:
            #             if AssetsSplits.objects.filter(belongs_to=each).filter(date=even['date']):
            #                 continue
            #             else:
            #                 new_split = each.assetssplits_set.create(date=even['date'], split=even['split'])
            #                 new_split.save()
            url = split_request_url.format(asset=(each.exchange_ticker + '.' + each.exchange.real_code))
            print("Getting url "+url)
            request = requests.get(url)
            try:
                answer = json.loads(request.text)
            except Exception as err:
                print(err, '\n', request.text)
                continue
            if len(answer):
                for even in answer:
                    if AssetsSplits.objects.filter(belongs_to=each).filter(date=even['date']):
                        continue
                    else:
                        new_split = each.assetssplits_set.create(date=even['date'], split=even['split'])
                        new_split.save()
    else:
        start_position = AssetsSplits.objects.latest('id').belongs_to
        skip = True
        for each in Asset.objects.filter(type__in=asset_type, exchange__active=True)[:1]:
            print(each.exchange_ticker)
            if skip:
                if start_position != each.name:
                    continue
                else:
                    skip = False
            else:
                # stock_exchanges = {'USA': ['US',], 'Russia': ['US', 'MCX'], 'Germany': ['INDX',]}
                # if each.country is None:
                #     continue
                # for stock_exchange in stock_exchanges[each.country.name]:
                #     request = requests.get(split_request_url.format(asset=(each.exchange_ticker + '.' + stock_exchange)))
                #     try:
                #         answer = json.loads(request.text)
                #     except Exception as err:
                #         print(err, '\n', request.text)
                #         continue
                #     if len(answer):
                #         for even in answer:
                #             if AssetsSplits.objects.filter(belongs_to=each).filter(date=even['date']):
                #                 continue
                #             else:
                #                 try:
                #                     new_split = each.assetssplits_set.create(date=even['date'], split=even['split'])
                #                     new_split.save()
                #                 except Exception as err:
                #                     print(err)
                #                     print('Date = ', even['date'], 'Split = ', even['split'])


                request = requests.get(split_request_url.format(asset=(each.exchange_ticker + '.' + each.exchange.real_code)))
                try:
                    answer = json.loads(request.text)
                except Exception as err:
                    print(err, '\n', request.text)
                    continue
                if len(answer):
                    for even in answer:
                        if AssetsSplits.objects.filter(belongs_to=each).filter(date=even['date']):
                            continue
                        else:
                            try:
                                new_split = each.assetssplits_set.create(date=even['date'], split=even['split'])
                                new_split.save()
                            except Exception as err:
                                print(err)
                                print('Date = ', even['date'], 'Split = ', even['split'])


def prices_update():
    for each in Asset.objects.filter(exchange__active=True)[:1]:
        if AssetsPrices.objects.filter(asset=each):
            print('Asset {} already has Splits'.format(each.exchange_ticker))
        else:
            #stock_exchanges = {'USA': ['US',], 'Russia': ['US', 'MCX'], 'Germany': ['INDX',]}
            print(each.exchange_ticker)
            # if each.country is None:
            #     continue
            # for stock_exchange in stock_exchanges[each.country.name]:
            intervals = ['d']
            for interval in intervals:
                print(prices_request_url.format(asset=(each.exchange_ticker + '.' + each.exchange.real_code),
                                                period=interval))
                request = requests.get(prices_request_url.format(asset=(each.exchange_ticker + '.' + each.exchange.real_code),
                                                                 period=interval), timeout=None)
                try:
                    answer = json.loads(request.text)
                except Exception as err:
                    print(err, '\n', request.text)
                    continue
                if len(answer):
                    for even in answer:
                        if AssetsPrices.objects.filter(asset=each).filter(interval=interval).filter(date=even['date']):
                            pass
                        else:
                            dates_of_splits = dict()
                            for date_of_split in AssetsSplits.objects.filter(belongs_to=each):
                                dates_of_splits[date_of_split.real_date] = date_of_split.split
                            dates = list(dates_of_splits.keys())
                            dates.sort()
                            pos = 0
                            while pos+1 <= len(dates):
                                if even['date'] > str(dates[pos]):
                                    pos += 1
                                else:
                                    price = even['close']
                                    for date in dates[pos:]:
                                        pos += 1
                                        try:
                                            split = dates_of_splits[date].split('/')
                                            price *= float(split[1])
                                            price /= float(split[0])
                                        except Exception as err:
                                            print(err)
                                            continue
                                    try:
                                        new_price = each.assetsprices_set.create(interval=interval,
                                                                                 price=even['close'],
                                                                                 date=even['date'],
                                                                                 price_after_split=price)
                                        new_price.save()
                                    except Exception as err:
                                        print('Error: ', err)
                                        print("Param's:\n",
                                              'Ticker =', each.exchange_ticker,
                                              'Price =', even['close'],
                                              'Date =', even['date'],
                                              'Price_after_split', price)
    finish = DatesOfPricesUpdates.objects.all().latest('date')
    finish.status = 'f'
    finish.save(update_fields=['status'])


def check():
    with open('log.txt', 'a', encoding='utf-8') as log:
        for each in Asset.objects.filter(type__in=asset_type, exchange__active=True):
            if AssetsPrices.objects.filter(asset=each):
                continue
            else:
                a = '{} {} \n'.format(each.exchange_ticker, each.name)
                log.write(a)


def recalculation():
    with open('recalculation_log.txt', 'a', encoding='utf-8') as log:
        for recalculating_asset in Asset.objects.filter(type__in=asset_type, exchange__active=True):
            print('{} {} \n'.format(recalculating_asset.exchange_ticker, recalculating_asset.name))
            log.write('{} {}\n'.format(recalculating_asset.exchange_ticker, recalculating_asset.name))
            for obj in AssetsPrices.objects.filter(asset=recalculating_asset):
                log.write('Object ID = {}\n'.format(obj.id))
                dates_of_splits = dict()
                for date_of_split in AssetsSplits.objects.filter(belongs_to=obj.asset):
                    dates_of_splits[date_of_split.real_date] = date_of_split.split
                dates = list(dates_of_splits.keys())
                dates.sort()
                price = obj.price
                for each_date in dates:
                    if obj.date > each_date:
                        continue
                    else:
                        try:
                            split = dates_of_splits[each_date].split('/')
                            price *= float(split[1])
                            price /= float(split[0])
                        except Exception as err:
                            print('{}\n'.format(err))
                            log.write('{}\n'.format(err))
                obj.price_after_split = price
                obj.save(update_fields=['price_after_split'])

#from backtest.update_assets_prices import *
#splits_update()
#prices_update()