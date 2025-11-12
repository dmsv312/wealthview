import asyncio
import aiohttp
import numpy as np
import json
from django.conf import settings

from core.integrations.eod import EODService

api_key = settings.EOD_SERVICE_API_KEY
url_web = settings.EOD_SERVICE_URL
json_fmt = settings.EOD_SERVICE_JSON_FMT


async def main(urls):
    eod_service = EODService()
    ret = await asyncio.gather(*[eod_service.make_request(url) for url in urls])
    return ret


# ticker - тикер актива
# exchange - биржа, на которой торгуется актив
# start_date - дата старта периода актива
# end_date - дата конца периода актива
def get_url(ticker, exchange, start_date, end_date):
    """Функция формирования url-запроса к ценам актива."""
    if exchange in ["NASDAQ", "NYSE ARCA", "NYSE", "BATS", "OTCQX"]:
        exchange = "US"

    # Составляем url для запроса по API
    rqStr = url_web + ticker + "." + exchange + "?" + "&from=" + start_date + "&to=" + end_date + api_key + json_fmt
    return rqStr


# ticker - тикер актива
# exchange - биржа, на которой торгуется актив
def get_live_url(ticker, exchange):
    """Функция формирования url-запроса к live-цене актива."""
    if exchange in ["NASDAQ", "NYSE ARCA", "NYSE", "BATS", "OTCQX"]:
        exchange = "US"

    # Составляем url для запроса по API
    rqStr = url_web.replace("/eod/", "/real-time/") + ticker + "." + exchange + "?" + api_key + json_fmt
    return rqStr


def get_split_data(split):
    splits_dates, splits_ratios, ratio = [], [], 0
    for i in range(len(split)):
        splits_dates = np.append(splits_dates, split[i]['date'])
        split[i]['split'] = split[i]['split'].split('/')
        ratio = float(split[i]['split'][0]) / float(split[i]['split'][1])
        splits_ratios = np.append(splits_ratios, ratio)

    return splits_dates, splits_ratios
