import asyncio
import datetime
import json

import aiohttp
from django.conf import settings
from django.core.cache import cache
from sentry_sdk import capture_exception


class EODService(object):
    access_token = settings.EOD_SERVICE_API_KEY_RAW
    cache_key = 'eod_http_request_'
    eod_host = 'https://eodhistoricaldata.com'

    async def cache_set(self, url, json_response):
        utcnow = datetime.datetime.utcnow()
        if '/real-time/' in url:
            clear_cache_at = utcnow + datetime.timedelta(minutes=5)
        else:
            clear_cache_at = (utcnow + datetime.timedelta(days=1)).replace(hour=1, minute=45)
        timeout = int((clear_cache_at - datetime.datetime.utcnow()).total_seconds())
        cache.set(f'{self.cache_key}{url}', json_response, timeout=timeout)

    async def cache_get(self, url):
        return cache.get(f'{self.cache_key}{url}')

    async def _make_request(self, session, url, counter=None, exc=None):
        """ рекурсивная внутреняя функция класса для выполнения запроса и при ошибке делая еще 3 попытки """
        if counter is None:
            counter = 0
        if counter > 3:
            raise exc or Exception('something wrong with eod service')
        try:
            async with session.get(url=url, verify_ssl=False) as response:
                response.raise_for_status()
                resp = await response.read()
                response_json = json.loads(resp)
                await self.cache_set(url, response_json)
                return response_json
        except aiohttp.ClientError as exc:
            counter += 1
            capture_exception(exc)
            return await self._make_request(session, url, counter, exc)

    async def make_request(self, url):
        """ базовая функция для выполнения запроса к eodhistoricaldata """
        cache_val = await self.cache_get(url)
        if cache_val:
            return cache_val

        async with aiohttp.ClientSession() as session:
            return await self._make_request(session, url)

    def get_exchange_url(self, exchange):
        return f"{self.eod_host}/api/exchanges/{exchange}?api_token={self.access_token}&fmt=json"

    def get_split_url(self, asset, date_from, date_to):
        return f'{self.eod_host}/api/splits/{asset}?api_token={self.access_token}&from={date_from}&to={date_to}&fmt=json'

    def get_price_url(self, asset):
        return f'{self.eod_host}/api/fundamentals/{asset}?api_token={self.access_token}&fmt=json'

    def get_splits(self, asset, date_from, date_to):
        url = self.get_split_url(asset, date_from, date_to)
        return asyncio.run(self.make_request(url))

    def get_assets(self, exchange):
        url = self.get_exchange_url(exchange)
        return asyncio.run(self.make_request(url))

    def get_prices(self, asset):
        url = self.get_price_url(asset)
        return asyncio.run(self.make_request(url))
