import json
import traceback
import numpy
import logging

from django.db.models import QuerySet
from django.conf import settings
from datetime import datetime

from algorithm.mvp_personal_account import analysingPortfolio, returnsPortfolioPeriod, dynamicPrices
from backtest.analyze import AnalyzePortfolio as BaseAnalyzePortfolio
from backtest.models import Asset, Type

logger = logging.getLogger('wealthview')


class AnalyzePortfolio(BaseAnalyzePortfolio):
    analysis_data_vars = ["bench_dates_days", "bench_close_days", "nr_dates_days", "nr_close_days", "all_dates",
                          "ptf_close_days", "forex_close_days", "ptf_start_date", "free_cash_rub",
                          "free_cash_usd", "abs_profit_by_periods",
                          "open_positions", "others_temporary", "start_prices", "weighted_avg_sum",
                          "unique_exchanges",
                          "myptf_close_days", "stats_param", "as_corr_matrix", "as_vol_beta", "risk-profile"]
    CASH_TYPE_SLUG = "CS"
    CASH_CHANGE_SLUG = "FX"
    ASSET_SLUG = ("ET", "ST")
    NR_USD_INFO = ("IDCOT10TR", "INDX")
    NR_RUB_INFO = ("RGBITR", "INDX")
    BASE_CACHE_VARS = ("portfolio_cache", "settings_cache", "dynamic_prices_cache", "analysis_date",
                       "portfolio_analysis_data", "ptf_total_cash")

    def __init__(self, portfolio):
        self.portfolio_analysis_data = {}
        self.portfolio = portfolio
        self.currency_ticker = portfolio.currency.ticker
        operations = portfolio.portfolio_operations.all()
        self.operations_ids = list(operations.values_list("id", flat=True))
        self.operations = self._serialize_operations(operations)

    def _get_nr_info(self, currency_ticker):
        if currency_ticker == "USD":
            return self.NR_USD_INFO
        elif currency_ticker == "RUB":
            return self.NR_RUB_INFO
        return "", ""

    @staticmethod
    def _serialize_operations(operations: QuerySet) -> list:
        """
        Convert operations queryset to the list of dicts. It is necessary to be able to validate new operations by
        updating this list (check "OperationAddView" for example)
        """
        operations_list = []
        for operation in operations:
            operations_list.append({
                "type": operation.type,
                "asset": operation.asset,
                "cost": operation.cost,
                "price": operation.price,
                "count": operation.count,
                "date": operation.date,
            })
        return operations_list

    def get_dynamic_prices_cache(self, analysis_data, forex_close_days):
        """Get cache information for operations dynamic params update"""
        open_positions = analysis_data["open_positions"]
        others_temporary = analysis_data["others_temporary"]
        start_prices = analysis_data["start_prices"]
        weighted_avg_sum = analysis_data["weighted_avg_sum"]
        unique_exchanges = analysis_data["unique_exchanges"]
        unique_exchanges = [i for i in unique_exchanges if i != " "]  # TODO: temp hardcode validation, fix later
        ptf_last_value = analysis_data["ptf_close_days"][1][-1]
        cash_last_value = forex_close_days[-1]
        free_cah_rub = analysis_data["free_cash_rub"]
        free_cah_usd = analysis_data["free_cash_usd"]
        data = {
            "average_prices": open_positions[3],
            "start_prices": start_prices,
            "quantity_open": open_positions[5],
            "weighted_avg_sum": weighted_avg_sum,
            "emitents": open_positions[0],
            "tickers": open_positions[1],
            "unique_exchanges": unique_exchanges,
            "cash": others_temporary[1],
            "ptf_last_value": ptf_last_value,
            "operations_ids": self.operations_ids,
            "ptf_total_cash": others_temporary[0],
            "free_cah_rub": free_cah_rub,
            "free_cah_usd": free_cah_usd,
            "portfolio_currency": self.portfolio.currency.ticker,
            "cash_last_value": cash_last_value,
        }
        return data

    def _get_operations_data(self, operations):
        """Get all possible operations in appropriate for lib format"""
        transactions, cash, cash_change, dividend = [], [], [], []
        for operation in operations:
            operation_type = operation.get("type").slug
            date = operation.get("date").strftime("%Y-%m-%d")
            asset = operation.get("asset")
            asset_name = asset.name
            ticker = asset.exchange_ticker
            exchange = asset.exchange.code if asset.exchange else ""
            cost = operation.get("cost")
            price = operation.get("price")
            count = operation.get("count")
            if operation_type in ["Buy", "Sell"] and asset.type.slug in self.ASSET_SLUG:
                transactions.append(([date, asset_name, ticker, exchange, operation_type, price, count]))
            elif operation_type in ["Input", "Output"] and asset.type.slug in self.CASH_TYPE_SLUG:
                cash.append([date, asset_name, ticker, operation_type, cost])
            elif operation_type in ["Buy", "Sell"] and asset.type.slug in self.CASH_CHANGE_SLUG:
                cash_change.append([date, ticker, operation_type, price, count])
            elif operation_type in ["Dividend"]:
                dividend.append([date, asset_name, ticker, exchange, operation_type, cost])
        return transactions, cash, cash_change, dividend

    def _get_corr_matrix(self, data):
        """Get values for correlation matrix"""
        corr_matrix = []
        # if period > 12 weeks
        if "as_corr_matrix" in data.keys():
            as_cor_matrix = data["as_corr_matrix"]
            tickers = data["as_vol_beta"][0]
            vol_tickers_and_bench = data["as_vol_beta"][1]
            beta_tickers_and_bench = data["as_vol_beta"][2]

            corr_matrix = []
            # map assets
            for i in range(len(tickers)):
                asset = Asset.objects.filter(exchange_ticker=tickers[i]).first()
                if asset:
                    corr_values = [value for value in as_cor_matrix[i] if str(value) != "nan"]
                    corr_matrix.append({"name": asset.name, "ticker": tickers[i],
                                        "corr_values": corr_values,
                                        "vol_tickers_and_bench": vol_tickers_and_bench[i],
                                        "beta_tickers_and_bench": beta_tickers_and_bench[i]})
        return corr_matrix

    def _get_plot_data(self, data):
        """Get values for сharts"""
        bench_price_change, ptf_price_change, nr_price_change = super()._get_plot_data(data)
        ptf_price_change = {"data": [list(i) for i in zip(data["all_dates"], data["ptf_close_days"][1])],
                            "dates": data["all_dates"]}
        return bench_price_change, ptf_price_change, nr_price_change

    @classmethod
    def get_relative_values_by_period(cls, start_date, end_date, portfolio, cache):
        """Recalculate portfolio values for the new selected period"""
        start_date = str(datetime.fromtimestamp(float(start_date) / 1000).date())
        end_date = str(datetime.fromtimestamp(float(end_date) / 1000).date())
        all_dates = numpy.array(cache["all_dates"])
        cash = cache["cash"]
        # старый полученный массив из кэша (пока пусть будет тут)
        ptf_values = numpy.array(cache["ptf_abs_values"])
        # мой новый полученный правильный массив из кэша
        my_ptf_values = numpy.array(cache["my_abs_values"])
        forex_close_days = numpy.array(cache["forex_close_days"])
        ptf_start_date = cache["ptf_start_date"]
        currency = portfolio.currency.ticker
        dates, values, weighted_s = returnsPortfolioPeriod(cash, currency, all_dates, my_ptf_values, forex_close_days,
                                                           ptf_start_date,
                                                           start_date, end_date)
        dates = [cls.date_to_timestamp_milliseconds(date) for date in dates]
        return list(zip(dates, values))

    @staticmethod
    def _get_cache_portfolio_params(cash, ptf_abs_values, forex_close_days, all_dates, ptf_start_date, my_abs_values):
        """Get cache values - need for the future recalculation of portfolio values"""
        data = {
            "cash": cash,
            "ptf_abs_values": ptf_abs_values.tolist(),
            "forex_close_days": forex_close_days.tolist(),
            "all_dates": all_dates.tolist(),
            "ptf_start_date": ptf_start_date,
            "my_abs_values": my_abs_values.tolist()
        }
        return data

    @classmethod
    def get_updated_operations_info(cls, dynamic_prices_cache):
        """Update information about open positions"""
        cache = dynamic_prices_cache
        data = {
            "iABPrices": [float(i) for i in cache.get("average_prices")[:-2]],  # [:-2] - remove cash values
            "iSPAs": cache.get("start_prices"),
            "iQOpen": [float(i) for i in cache.get("quantity_open")[:-2]],  # [:-2] - remove cash values
            "iWASum": cache.get("weighted_avg_sum"),
            "iOEmitents": cache.get("emitents")[:-2],  # [:-2] - remove cash values
            "iOTickers": numpy.array(cache.get("tickers")[:-2]),  # [:-2] - remove cash values
            "iOExchanges": numpy.array(cache.get("unique_exchanges")),
            "iCashLast": cache.get("cash"),
            "iCashLastRUB": cache.get("free_cah_rub"),
            "iCashLastUSD": cache.get("free_cah_usd"),
            "iPtfCloseLast": cache.get("ptf_last_value"),
            "iForexPriceLast": cache.get("cash_last_value"),
            "iForex": cache.get("portfolio_currency")
        }
        result = dynamicPrices(**data)
        total_cash = result[0][0]
        open_positions = result[1]
        open_positions = cls._get_open_positions(open_positions)
        return total_cash, open_positions

    @classmethod
    def _get_open_positions(cls, operations):
        open_positions = []
        titles = ["name", "ticker", "exchange_code", "average_price", "current_price", "quantity_open", "ptf_percent",
                  "invest_sum", "current_cost", "percent_change"]
        for i in range(len(operations[0])):
            operation_dict = {}
            for index, operation in enumerate(operations):
                operation_dict.update({titles[index]: operation[i]})
            open_positions.append(operation_dict)
        open_positions = [i for i in open_positions if float(i["quantity_open"]) != float(0.0)]
        return open_positions

    @staticmethod
    def _get_cash_by_assets(open_positions):
        """Get data for pie diagram.

        Information about assets allocation (by asset class, by asset ticker)
        """
        asset_types = Type.objects.all()
        cash_by_asset_type = {asset_type.title: 0 for asset_type in asset_types}
        # get ticker cash by asset names
        cash_by_asset_ticker = [{"name": item["ticker"], "y": float(item["ptf_percent"]), "asset_name": item["name"],
                                 "asset_exchange_code": item["exchange_code"], "asset_ticker": item["ticker"]}
                                for item in open_positions if float(item["ptf_percent"]) != 0]

        # get cash by asset types
        for asset in cash_by_asset_ticker:
            asset_instance = Asset.objects.get(exchange_ticker=asset["asset_ticker"], exchange__code=asset["asset_exchange_code"])
            asset_type = asset_instance.type.title
            cash_by_asset_type[asset_type] += asset["y"]
        cash_by_asset_type = [{"name": key, "y": value} for
                              key, value in cash_by_asset_type.items() if value != 0]
        return json.dumps(cash_by_asset_ticker), json.dumps(cash_by_asset_type)

    def get_analysis_data(self):
        """Base method for getting all information about profile portfolio"""
        transactions, cash, cash_change, dividend = self._get_operations_data(self.operations)
        # self.assets_tickers = self._get_assets_tickers(self.operations)
        benchmark_ticker = self.portfolio.benchmark.exchange_ticker
        benchmark_exchange = self.portfolio.benchmark.exchange.code
        nr_ticker, nr_exchange = self._get_nr_info(self.currency_ticker)
        try:
            result_data = analysingPortfolio(transactions, cash, cash_change, dividend, benchmark_ticker,
                                             benchmark_exchange, nr_ticker, nr_exchange, self.currency_ticker, 'None',
                                             'None')
        except Exception as ex:
            # TODO поставить везде отлов ошибок алгоритма в сентри
            from sentry_sdk import capture_exception
            capture_exception(ex)
            return {"analysis_errors": {"text": "Произошла ошибка", 'text_detail': 'Произошла ошибка'}}

        if isinstance(result_data, str):
            return {"analysis_errors": {"text": 'Произошла ошибка', 'text_detail': result_data}}

        result_data = dict(zip(self.analysis_data_vars, result_data))  # initiate vars
        ptf_abs_values = result_data.get("ptf_close_days")[1]
        my_abs_values = result_data.get("myptf_close_days")[1]
        forex_close_days = result_data.pop("forex_close_days")
        all_dates = result_data.get("all_dates")
        result_data = {key: self._array_to_list_deep(value) for key, value in result_data.items()}
        dynamic_prices_cache = self.get_dynamic_prices_cache(result_data, forex_close_days)
        portfolio_cache = self._get_cache_portfolio_params(cash, ptf_abs_values, forex_close_days, all_dates,
                                                           result_data["ptf_start_date"], my_abs_values)
        settings_cache = {"benchmark_id": self.portfolio.benchmark.id,
                          "currency_ticker": self.portfolio.currency.ticker}
        open_positions = self._get_open_positions(result_data["open_positions"])
        cash_by_asset_ticker, cash_by_asset_type = self._get_cash_by_assets(open_positions)

        if len(result_data) == 20:
            self.portfolio_analysis_data["risk_profile_number"] = result_data["risk-profile"][0]
            self.portfolio_analysis_data["risk_profile_name"] = result_data["risk-profile"][1]
        else:
            self.portfolio_analysis_data["risk_profile_number"] = ""
            self.portfolio_analysis_data["risk_profile_name"] = ""

        self.portfolio_analysis_data["bench_dates_days"] = result_data["bench_dates_days"]
        self.portfolio_analysis_data["nr_dates_days"] = result_data["nr_dates_days"]
        self.portfolio_analysis_data["cash_by_asset_ticker"] = cash_by_asset_ticker
        self.portfolio_analysis_data["cash_by_asset_type"] = cash_by_asset_type
        self.portfolio_analysis_data["no_risk_rate"] = self._get_no_risk_rate()
        self.portfolio_analysis_data.update(self._get_base_analysis_data(result_data, "account"))
        self.portfolio_analysis_data["benchmark_name"] = self.portfolio.benchmark.name
        self.portfolio_analysis_data.pop("max_start_date")
        ptf_total_cash = dynamic_prices_cache.get("ptf_total_cash")
        analysis_date = datetime.now().strftime("%d-%m-%Y")
        return {
            "portfolio_analysis_data": self.portfolio_analysis_data,
            "open_positions": open_positions,
            "ptf_total_cash": ptf_total_cash,
            "portfolio_cache": portfolio_cache,
            "settings_cache": settings_cache,
            "dynamic_prices_cache": dynamic_prices_cache,
            "analysis_date": analysis_date
        }
