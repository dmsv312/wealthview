import json
import pytz
import numpy as np

from datetime import datetime

from .models import Type, Asset
from algorithm.mvp_back_test import back_test_portfolio

class AnalyzePortfolio:
    analysis_data_vars = ["cash_tickers_names", "exchanges", "cash_tickers_share", "bench_dates_days",
                          "bench_close_days",
                          "nr_dates_days", "nr_close_days", "all_dates", "ptf_close_days", "abs_profit_by_periods",
                          "abs_values", "stats_param", "as_corr_matrix", "as_vol_beta", "risk-profile"]
    no_risk_exchange = "INDX"
    invalid_stats_values = ["-", "inf", "-inf", "nan"]

    def __init__(self, arr_tickets, arr_exchange, arr_tickets_share, input_start_date, input_end_date,
                 exchange_ticker, exchange_id, currency_ticker, investment_names, rebalancing):
        self.arr_tickets = arr_tickets
        self.arr_exchange = arr_exchange
        self.arr_tickets_share = arr_tickets_share
        self.input_start_date = input_start_date
        self.input_end_date = input_end_date
        self.exchange_ticker = exchange_ticker
        self.exchange_id = exchange_id
        self.currency_ticker = currency_ticker
        self.investment_names = investment_names
        self.analysis_data = {}
        self.no_risk_rate = self._get_no_risk_rate()
        self.rebalancing = rebalancing

    @classmethod
    def get_relative_values_by_period(cls, start_date, end_date, dates, abs_values):
        """Recalculate portfolio values to get relative values for user selected period

        This is the function from the 'mvp_back_test' library
        """
        dates, abs_values = [np.array(i) for i in [dates, abs_values]]
        start_date = float(start_date)
        end_date = float(end_date)
        if start_date and end_date in dates:
            start_index, = np.where(dates == start_date)[0]
            end_index, = np.where(dates == end_date)[0]
            ptf_values, ptf_dates = [], []  # Даты, цены закрытия портфеля произвольного периода
            for day in range(start_index, end_index + 1):
                ptf_dates = np.append(ptf_dates, dates[day])
                ptf_values = np.append(ptf_values, 100 * (abs_values[day] / abs_values[start_index] - 1))
            return list(zip(ptf_dates, ptf_values))
        return None

    @classmethod
    def date_to_timestamp_milliseconds(cls, date):
        """Convert dates to timestamp format in milliseconds"""
        date_object = datetime.strptime(date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0,
                                                                  tzinfo=pytz.utc)
        return date_object.timestamp() * 1000

    def _get_no_risk_rate(self):
        """"Get risk-free rate"""
        if self.currency_ticker == "USD":
            return {"ticker": "IDCOT10TR", "name": "ICE U.S. Treasury 10-20 Year TR"}
        elif self.currency_ticker == "RUB":
            return {"ticker": "RGBITR", "name": "Russian Government Bond Index"}

    def _array_to_list_deep(self, array):
        """Convert numpy array to list"""
        if isinstance(array, np.ndarray):
            return self._array_to_list_deep(array.tolist())
        elif isinstance(array, (list, tuple)):
            return [self._array_to_list_deep(item) for item in array]
        else:
            return array

    def _get_plot_data(self, data):
        """Get cost of portfolio, inflation, benchmark"""
        # convert dates to timestamp milliseconds
        data["all_dates"] = [self.date_to_timestamp_milliseconds(date) for date in data["all_dates"]]
        data["bench_dates_days"] = [self.date_to_timestamp_milliseconds(date) for date in
                                    data["bench_dates_days"]]
        data["nr_dates_days"] = [self.date_to_timestamp_milliseconds(date) for date in
                                 data["nr_dates_days"]]
        ptf_price_change = {"dates": data["all_dates"], "values": data["ptf_close_days"]}
        nr_price_change = {"dates": data["nr_dates_days"], "values": data["nr_close_days"]}
        bench_price_change = {"dates": data["bench_dates_days"], "values": data["bench_close_days"]}
        return bench_price_change, ptf_price_change, nr_price_change

    @staticmethod
    def _get_abs_profit_by_periods(data, source):
        """Get absolute profit values by periods"""
        values = []
        names = ["ptf", "bench", "nr"]
        abs_profit_by_periods_vars = ["one_month", "three_month", "six_month", "one_year"]
        for i in range(len(data["abs_profit_by_periods"])):
            data_array = data["abs_profit_by_periods"][i]
            if source == "account":
                yesterday = data_array.pop(-1)
                all_values = data_array.pop(-1)
                data_dict = {"all": all_values, "yesterday": yesterday}
            else:
                all_values = data_array.pop(-1)
                data_dict = {"all": all_values}
            if data_array:
                ytd_values = data_array.pop(-1)
                data_dict.update({"ytd": ytd_values})
            data_array = [value for value in data_array]
            data_dict.update(dict(zip(abs_profit_by_periods_vars, data_array)))
            values.append(data_dict)
        return dict(zip(names, values))

    def _get_stats_param(self, data):
        """Get portfolio statistics coefficients"""
        stats_param = {}
        if "stats_param" in data.keys():
            stats_param_names = ["gagr", "vol", "sharp", "alpha", "beta", "cor", "r_square"]
            stats_param_values = data.get("stats_param")
            stats_param.update(dict(zip(stats_param_names, stats_param_values)))
            # stats_param = {key: value for key, value in stats_param.items() if
            #                str(value["value"]) not in self.invalid_stats_values}
        return stats_param

    @staticmethod
    def _get_cash_by_assets(data):
        """Get data for pie diagram.

        Information about assets allocation (by type, by name)
        """
        asset_types = Type.objects.all()
        asset_types_values = {asset_type.slug: {"title": asset_type.title, "value": 0} for asset_type in
                              asset_types}
        asset_names = data["cash_tickers_names"]
        asset_cash = data["cash_tickers_share"]
        asset_exchanges = data["exchanges"]

        # get ticker cash by  name
        cash_by_asset_ticker = [{"name": asset_names[i], "y": asset_cash[i],
                                 "asset_exchange_code": asset_exchanges[i], "asset_ticker": asset_names[i]}
                                for i in range(len(asset_exchanges))]

        # get cash by type
        for asset in cash_by_asset_ticker:
            if asset["name"] != "Cash":
                asset_object = Asset.objects.get(exchange_ticker=asset["name"],
                                                 exchange__code=asset["asset_exchange_code"])
                asset_type = asset_object.type.slug
                asset_types_values[asset_type]["value"] += asset["y"]
        cash_by_asset_type = [{"name": ticker_type_value["title"], "y": ticker_type_value["value"]} for
                              ticker_type_value in asset_types_values.values()]

        # exclude null values
        cash_by_asset_ticker = [i for i in cash_by_asset_ticker if i["y"] != 0]
        cash_by_asset_type = [i for i in cash_by_asset_type if i["y"] != 0]
        return json.dumps(cash_by_asset_ticker), json.dumps(cash_by_asset_type)

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
            for i in range(len(as_cor_matrix)):
                corr_matrix.append({"name": self.investment_names[tickers[i]], "ticker": tickers[i],
                                    "corr_values": as_cor_matrix[i],
                                    "vol_tickers_and_bench": vol_tickers_and_bench[i],
                                    "beta_tickers_and_bench": beta_tickers_and_bench[i]})
        return corr_matrix

    def _get_base_analysis_data(self, result_data, source):
        """Common data for analyze in backtest and personal account:
           price change graph, correlation matrix, absolute profit by periods, statistic params, dates array
         """
        max_start_date = result_data["bench_dates_days"][0]
        max_start_date = datetime.strptime(max_start_date, "%Y-%m-%d")
        stats_param = self._get_stats_param(result_data)
        all_dates = result_data["all_dates"]
        corr_matrix = self._get_corr_matrix(result_data)
        bench_price_change, ptf_price_change, nr_price_change = self._get_plot_data(result_data)
        abs_profit_by_periods = self._get_abs_profit_by_periods(result_data, source)
        return {"max_start_date": max_start_date, "stats_param": stats_param, "all_dates": all_dates,
                "corr_matrix": corr_matrix, "bench_price_change": bench_price_change,
                "ptf_price_change": ptf_price_change, "nr_price_change": nr_price_change,
                "abs_profit_by_periods": abs_profit_by_periods}

    def get_analysis_data(self):
        """Base method for getting all information"""
        # get data from analyze library
        result_data = back_test_portfolio(self.arr_tickets, self.arr_exchange, self.arr_tickets_share,
                                        self.input_start_date, self.input_end_date, self.exchange_ticker,
                                        self.exchange_id, self.no_risk_rate["ticker"], self.no_risk_exchange,
                                        self.currency_ticker, self.rebalancing)
        # get not converted to list values
        # cash_tickers_share = result_data[1]
        # abs_values = result_data[9]
        # convert all numpy arrays to lists
        if isinstance(result_data, str):
            self.analysis_data["analysis_errors"] = result_data
            return self.analysis_data
        result_data = self._array_to_list_deep(result_data)  # convert all numpy arrays to list
        result_data = dict(zip(self.analysis_data_vars, result_data))  # initiate vars
        self.analysis_data.update(self._get_base_analysis_data(result_data, "backtest"))
        # get backtest specific data
        cash_by_assets = self._get_cash_by_assets(result_data)
        if len(result_data) == 15:
            self.analysis_data["risk_profile_number"] = result_data["risk-profile"][0]
            self.analysis_data["risk_profile_name"] = result_data["risk-profile"][1]

        self.analysis_data["cash_by_asset_ticker"] = cash_by_assets[0]
        self.analysis_data["cash_by_asset_type"] = cash_by_assets[1]
        self.analysis_data["no_risk_rate"] = self.no_risk_rate
        self.analysis_data["abs_values"] = result_data.get("abs_values")
        self.analysis_data["cash_tickers_share"] = result_data.get("cash_tickers_share")
        self.analysis_data["analysis_errors"] = ""
        return self.analysis_data
